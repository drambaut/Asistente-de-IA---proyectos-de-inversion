
# app.py
from flask import Flask, render_template, request, jsonify, session, send_from_directory, url_for
from flask_cors import CORS
import os, logging, re, httpx
from dotenv import load_dotenv
from openai import AzureOpenAI

from utils import (
    ask_markdown_azure,
    generate_project_document,
    _md_link, _is_yes, _is_no,
    parse_causas_xlsx, parse_objetivos_xlsx,
    save_tree_json, process_uploaded_excel,
    causas_tree_to_markdown, objetivos_tree_to_markdown,
    conversation_flow, validate_excel_bytes, 
    SYSTEM_PRIMER
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'idec_secret_key_change_in_production')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(app.static_folder, 'documents')
FORMULARIOS_DIR = os.path.join(app.static_folder, 'formularios')
FORMULARIOS_JSON_DIR = os.path.join(app.static_folder, 'formularios_json')
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(FORMULARIOS_DIR, exist_ok=True)
os.makedirs(FORMULARIOS_JSON_DIR, exist_ok=True)

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
    http_client=httpx.Client(verify=False)
)

@app.route('/')
def index():
    session.clear()
    session['current_step'] = 'intro_bienvenida'
    session['responses'] = {}
    session['mode'] = 'flow'
    return render_template('index.html')

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(DOCUMENTS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error descargando archivo: {e}")
        return "Error al descargar el archivo", 404

@app.route('/plantilla/<tipo>')
def plantilla(tipo):
    fname = 'PlantillaCausa.xlsx' if tipo == 'causa' else 'PlantillaObjetivo.xlsx' if tipo == 'objetivo' else None
    if not fname: return "Tipo inválido", 400
    path = os.path.join(BASE_DIR, fname)
    if not os.path.isfile(path): return "Plantilla no encontrada", 404
    return send_from_directory(BASE_DIR, fname, as_attachment=True)

# ---------- Upload + validación + parse + JSON ----------
from utils import validate_excel_bytes

@app.route('/api/upload_formulario', methods=['POST'])
def upload_formulario():
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "Archivo no recibido"}), 400
    f = request.files['file']
    tipo = (request.form.get('tipo') or '').strip().lower()
    if tipo not in ('causa', 'objetivo'):
        return jsonify({"ok": False, "error": "Tipo inválido"}), 400

    # Extensión
    original_name = f.filename or ''
    if not original_name.lower().endswith('.xlsx'):
        return jsonify({"ok": False, "error_code": "not_xlsx", "error": "El archivo debe ser un Excel .xlsx."}), 400

    # Validación en memoria
    data = f.read()
    ok, code, message = validate_excel_bytes(tipo, data, start_row=3)
    if not ok:
        return jsonify({"ok": False, "error_code": code, "error": message}), 400

    # Guardar + parsear
    proyecto = session.get('responses', {}).get('nombre_proyecto', 'proyecto')
    slug = re.sub(r'[^A-Za-z0-9_\-]+', '_', proyecto).strip('_') or 'proyecto'
    filename = f"{tipo}-{slug}.xlsx"
    save_path = os.path.join(FORMULARIOS_DIR, filename)
    with open(save_path, 'wb') as out:
        out.write(data)

    responses = session.get('responses', {})
    responses[f"upload_{tipo}"] = filename
    session['responses'] = responses

    try:
        info = process_uploaded_excel(tipo, save_path, FORMULARIOS_JSON_DIR)
        preview_md = info.get("preview_md")
        json_path = info.get("json_path")
        json_rel  = os.path.relpath(json_path, app.static_folder).replace('\\','/')
        if tipo == 'causa':
            session['causas_tree'] = info.get("tree")
        else:
            session['objetivos_tree'] = info.get("tree")
    except Exception as e:
        logger.exception("Error procesando Excel subido")
        return jsonify({"ok": False, "error_code": "parse_error", "error": "No se pudo procesar el Excel. Verifique la plantilla."}), 400

    return jsonify({
        "ok": True,
        "filename": filename,
        "json_file": json_rel,
        "preview_md": preview_md
    })

@app.route('/reset', methods=['POST'])
def reset_conversation():
    session.clear()
    session['current_step'] = 'intro_bienvenida'
    session['responses'] = {}
    session['mode'] = 'flow'
    return jsonify({"status": "ok", "message": "Conversación reiniciada"})

# ---------- Chat Libre ----------
def _bootstrap_alt_explanation(topic_md: str):
    session['mode'] = 'alt'
    system_msg = {"role": "system", "content": SYSTEM_PRIMER + "\nResponde SIEMPRE en Markdown claro, con viñetas y ejemplo."}
    user_msg   = {"role": "user", "content": f"{topic_md}\n\nTermina con: 'Cuando estés listo, escribe **Finalizar** para volver al flujo.'"}  # noqa: E501
    md = ask_markdown_azure([system_msg, user_msg], client=client, max_tokens=1000, temperature=0.4)
    return "💬 Has activado el **Chat Libre** para resolver esta duda.\n\n" + md

@app.route('/api/chat_alt', methods=['POST'])
def chat_alt():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    session['mode'] = "alt"

    if user_message.lower() == "finalizar":
        session['mode'] = "flow"
        next_after = session.pop('after_alt_next_step', None)
        if next_after: session['current_step'] = next_after
        session['resume_from_alt'] = True
        return jsonify({
            "response": "✅ Has finalizado el chat libre. Volvemos al flujo normal.",
            "options": ["Continuar flujo"],
            "format": "markdown"
        })

    md = ask_markdown_azure(
        [{"role":"system","content":SYSTEM_PRIMER + "\nResponde en Markdown válido, sin HTML."},
         {"role":"user","content":user_message}],
        client=client,
        model_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        max_tokens=1500, temperature=0.4, max_rounds=3
    )
    return jsonify({"response": md, "format": "markdown"})

# ---------- Flujo ----------
def _upload_prompt_with_link(step_key: str) -> str:
    if step_key == 'upload_causas':
        url = url_for('plantilla', tipo='causa')
        return f"**Cargar plantilla de causas.**\n\n1. Descargue la plantilla.\n2. Diligénciela.\n3. Súbala en el recuadro que aparece debajo.\n\n**Descargar plantilla:** [PlantillaCausa.xlsx]({url})"
    else:
        url = url_for('plantilla', tipo='objetivo')
        return f"**Cargar plantilla de objetivos.**\n\n1. Descargue la plantilla.\n2. Diligénciela.\n3. Súbala en el recuadro que aparece debajo.\n\n**Descargar plantilla:** [PlantillaObjetivo.xlsx]({url})"

@app.route('/api/chat', methods=['POST'])
def chat():
    if session.get("mode") == "alt":
        return chat_alt()

    data = request.get_json() or {}
    user_message = (data.get('message') or '').strip()
    user_lower = user_message.lower()

    current_step = session.get('current_step', 'intro_bienvenida')
    responses = session.get('responses', {})

    # Inicio rápido
    if current_step == 'intro_bienvenida' and user_lower in ('iniciar', 'start'):
        intro = conversation_flow['intro_bienvenida']
        return jsonify({"response": intro['prompt'], "current_step": "intro_bienvenida", "options": intro.get('options', []), "format": "markdown"})

    # Intro options
    if current_step == 'intro_bienvenida' and user_lower == 'tengo dudas respecto al proceso, me gustaría resolverlas antes de empezar':
        session['current_step'] = 'gate_1_ciclo'
        step = conversation_flow['gate_1_ciclo']
        return jsonify({"response": step['prompt'], "current_step": "gate_1_ciclo", "options": step['options'], "format": "markdown"})

    if current_step == 'intro_bienvenida' and user_lower == 'sí, entiendo el proceso y deseo continuar':
        session['current_step'] = conversation_flow['intro_bienvenida']['next_step']
        step = conversation_flow[session['current_step']]
        payload = {"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"}
        if "options" in step: payload["options"] = step["options"]
        return jsonify(payload)

    # Reanudar del chat libre
    if session.pop('resume_from_alt', False) or user_lower in ('continuar flujo', 'volver al flujo'):
        step_key = session.get('current_step', 'intro_bienvenida')
        step_conf = conversation_flow.get(step_key, {})
        resp_text = step_conf.get("prompt", "…")

        if step_key == 'idec_componentes':
            step = conversation_flow['idec_componentes']
            return jsonify({
                "response": step['prompt'] + "\n\nSelecciona una o más tarjetas y pulsa **Confirmar**.",
                "current_step": "idec_componentes",
                "format": "markdown",
                "multiselect": {
                    "items": [
                        "Gobernanza de datos",
                        "Interoperabilidad",
                        "Herramientas técnicas y tecnológicas",
                        "Seguridad y privacidad de datos",
                        "Datos",
                        "Aprovechamiento de datos"
                    ],
                    "submit_text": "Confirmar"
                }
            })

        if step_key in ('upload_causas','upload_objetivos'):
            resp_text = _upload_prompt_with_link(step_key)
            tipo = 'causa' if step_key == 'upload_causas' else 'objetivo'
            return jsonify({
                "response": resp_text, "current_step": step_key, "format": "markdown",
                "upload": {"expect_upload": True, "tipo": tipo, "download_url": url_for('plantilla', tipo=tipo)}
            })
        payload = {"response": resp_text, "current_step": step_key, "format": "markdown"}
        if "options" in step_conf: payload["options"] = step_conf["options"]
        return jsonify(payload)

    # Gates
    if current_step == 'gate_1_ciclo':
        if _is_yes(user_lower):
            session['current_step'] = conversation_flow['gate_1_ciclo']['next_step']
            step = conversation_flow['gate_2_herramienta']
            return jsonify({"response": step['prompt'], "current_step": "gate_2_herramienta", "options": step['options'], "format": "markdown"})
        elif _is_no(user_lower):
            session['after_alt_next_step'] = "gate_2_herramienta"
            md = _bootstrap_alt_explanation("Explica el ciclo de inversión pública y sus fases principales.")
            return jsonify({"response": md, "format": "markdown"})
        else:
            step = conversation_flow['gate_1_ciclo']
            return jsonify({"response": step['prompt'], "current_step": "gate_1_ciclo", "options": step['options'], "format": "markdown"})

    if current_step == 'gate_2_herramienta':
        if _is_yes(user_lower):
            session['current_step'] = conversation_flow['gate_2_herramienta']['next_step']
            step = conversation_flow[session['current_step']]
            payload = {"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"}
            if "options" in step: payload["options"] = step["options"]
            return jsonify(payload)
        elif _is_no(user_lower):
            session['after_alt_next_step'] = "pregunta_3_entidad"
            md = _bootstrap_alt_explanation("Explica por qué esta herramienta es de orientación y cómo el borrador sirve como insumo en formulación (MGA).")
            return jsonify({"response": md, "format": "markdown"})
        else:
            step = conversation_flow['gate_2_herramienta']
            return jsonify({"response": step['prompt'], "current_step": "gate_2_herramienta", "options": step['options'], "format": "markdown"})

    # Registro inicial simple
    if current_step == 'rol_abierto' and user_message:
        responses[current_step] = user_message
        session['responses'] = responses
        session['current_step'] = 'elige_vertical'
        step = conversation_flow['elige_vertical']
        return jsonify({"response": step['prompt'], "current_step": "elige_vertical", "options": step['options'], "format": "markdown"})

    # Elegir vertical
    if current_step == 'elige_vertical':
        choice = user_lower.strip()
        if 'cerrar la conversación' in choice or choice == 'no' or choice.startswith('no '):
            session['current_step'] = 'finalizado'
            msg = "❌ Este asistente solo atiende proyectos **IDEC/IA**. Se cierra la conversación. Usa *Reiniciar* para empezar de nuevo."
            return jsonify({"response": msg, "current_step": "finalizado", "format": "markdown"})
        elif 'idec' in choice:
            responses['vertical'] = 'IDEC'; session['responses'] = responses
            session['current_step'] = 'idec_componentes'
            step = conversation_flow['idec_componentes']
            return jsonify({
                "response": step['prompt'] + "\n\nSelecciona una o más tarjetas y pulsa **Confirmar**.",
                "current_step": "idec_componentes",
                "format": "markdown",
                "multiselect": {
                    "items": [
                        "Gobernanza de datos",
                        "Interoperabilidad",
                        "Herramientas técnicas y tecnológicas",
                        "Seguridad y privacidad de datos",
                        "Datos",
                        "Aprovechamiento de datos"
                    ],
                    "submit_text": "Confirmar"
                }
            })
        elif 'ia' in choice:
            responses['vertical'] = 'IA'; session['responses'] = responses
            session['current_step'] = conversation_flow['elige_vertical']['next_step']  # nombre_proyecto
            step = conversation_flow[session['current_step']]
            return jsonify({"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"})
        else:
            step = conversation_flow['elige_vertical']
            return jsonify({"response": step['prompt'], "current_step": "elige_vertical", "options": step['options'], "format": "markdown"})

    # IDEC multiselección
    if current_step == 'idec_componentes':
        if user_message.startswith('__msel__:'):
            raw = user_message.split(':', 1)[1]
            comps = [c.strip() for c in raw.split('|') if c.strip()]
            if comps:
                responses['idec_componentes'] = comps
                session['responses'] = responses
                session['current_step'] = conversation_flow['idec_componentes']['next_step']  # nombre_proyecto
                step = conversation_flow[session['current_step']]
                return jsonify({"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"})
        step = conversation_flow['idec_componentes']
        return jsonify({
            "response": step['prompt'] + "\n\nSelecciona una o más tarjetas y pulsa **Confirmar**.",
            "current_step": "idec_componentes",
            "format": "markdown",
            "multiselect": {
                "items": [
                    "Gobernanza de datos",
                    "Interoperabilidad",
                    "Herramientas técnicas y tecnológicas",
                    "Seguridad y privacidad de datos",
                    "Datos",
                    "Aprovechamiento de datos"
                ],
                "submit_text": "Confirmar"
            }
        })

    # PASOS DE CARGA
    if current_step in ('upload_causas', 'upload_objetivos'):
        step_key = current_step
        tipo = 'causa' if step_key == 'upload_causas' else 'objetivo'
        required_flag = f"upload_{tipo}"

        if re.search(r'\b(continuar|siguiente)\b', user_lower):
            if required_flag in session.get('responses', {}):
                next_step = conversation_flow[step_key]['next_step']
                session['current_step'] = next_step
                step_conf = conversation_flow[next_step]
                text = step_conf.get("prompt", "…")
                payload = {"response": text, "current_step": next_step, "format": "markdown"}
                if "options" in step_conf: payload["options"] = step_conf["options"]
                if next_step in ('upload_causas', 'upload_objetivos'):
                    next_tipo = 'causa' if next_step == 'upload_causas' else 'objetivo'
                    payload["response"] = _upload_prompt_with_link(next_step)
                    payload["upload"] = {"expect_upload": True, "tipo": next_tipo, "download_url": url_for('plantilla', tipo=next_tipo)}
                return jsonify(payload)
            else:
                text = _upload_prompt_with_link(step_key) + "\n\n> ⚠️ Aún no has subido el archivo. Por favor súbelo y luego escribe **Continuar**."
                return jsonify({
                    "response": text, "current_step": step_key, "format": "markdown",
                    "upload": {"expect_upload": True, "tipo": tipo, "download_url": url_for('plantilla', tipo=tipo)}
                })

        text = _upload_prompt_with_link(step_key)
        return jsonify({
            "response": text, "current_step": step_key, "format": "markdown",
            "upload": {"expect_upload": True, "tipo": tipo, "download_url": url_for('plantilla', tipo=tipo)}
        })

    # Guardar y avanzar (genérico)
    responses[current_step] = user_message
    session['responses'] = responses

    next_step = conversation_flow.get(current_step, {}).get("next_step")
    if (not next_step) or (next_step == "finalizado"):
        session['current_step'] = "finalizado"
        # ---- Generar documento enriquecido con árboles ----
        filepath = generate_project_document(
            responses,
            client=client,
            documents_dir=DOCUMENTS_DIR,
            causas_tree=session.get('causas_tree'),
            objetivos_tree=session.get('objetivos_tree'),
            formularios_json_dir=FORMULARIOS_JSON_DIR
        )
        filename = os.path.basename(filepath)
        md_link = _md_link(url_for('download_file', filename=filename), "Descargar documento")
        return jsonify({"response": f"✅ Flujo completado. Documento generado. {md_link}", "current_step": "finalizado", "format": "markdown"})

    session['current_step'] = next_step
    step_conf = conversation_flow.get(next_step, {})
    text = step_conf.get("prompt", "…")
    payload = {"response": text, "current_step": next_step, "format": "markdown"}
    if "options" in step_conf: payload["options"] = step_conf["options"]
    if next_step in ('upload_causas','upload_objetivos'):
        next_tipo = 'causa' if next_step == 'upload_causas' else 'objetivo'
        payload["response"] = _upload_prompt_with_link(next_step)
        payload["upload"]  = {"expect_upload": True, "tipo": next_tipo, "download_url": url_for('plantilla', tipo=next_tipo)}
    return jsonify(payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
