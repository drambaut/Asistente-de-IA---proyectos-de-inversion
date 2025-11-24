
# app.py
from flask import send_file, Flask, render_template, request, jsonify, session, send_from_directory, url_for
from flask_cors import CORS
import os, logging, re, httpx, io, zipfile
from dotenv import load_dotenv
from openai import AzureOpenAI

from utils import (
    ask_markdown_azure,
    generate_project_document,
    _md_link, _is_yes, _is_no,
    save_tree_json, process_uploaded_excel,
    causas_tree_to_markdown, objetivos_tree_to_markdown,
    conversation_flow,
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

@app.route('/download_templates')
def download_templates():
    # Ruta a las plantillas de Excel
    templates_folder = os.path.join(BASE_DIR, "plantillas_excel")
    
    if not os.path.exists(templates_folder):
        logger.error(f"La carpeta de plantillas no existe: {templates_folder}")
        return "Carpeta de plantillas no encontrada", 404

    # Obtener todos los archivos Excel de la carpeta
    excel_files = []
    for root, _, files in os.walk(templates_folder):
        for file in files:
            if file.lower().endswith(('.xlsx', '.xls')):
                file_path = os.path.join(root, file)
                excel_files.append((file_path, file))
    
    if not excel_files:
        logger.error(f"No se encontraron archivos Excel en: {templates_folder}")
        return "No se encontraron plantillas", 404
    
    # Si solo hay un archivo, descargarlo directamente
    if len(excel_files) == 1:
        file_path, filename = excel_files[0]
        return send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    # Si hay múltiples archivos, crear ZIP
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path, filename in excel_files:
            zf.write(file_path, filename)
    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='plantillas_excel.zip'
    )

@app.route('/download_manual')
def download_manual():
    # Buscar manual en diferentes ubicaciones y formatos
    possible_names = [
        'manual_de_uso.pdf',
        'manual_de_uso.docx',
        'Manual_de_Uso.pdf',
        'Manual_de_Uso.docx',
        'manual.pdf',
        'Manual.pdf'
    ]
    
    # Buscar en static/documents y en static
    search_paths = [
        DOCUMENTS_DIR,
        app.static_folder
    ]
    
    for search_path in search_paths:
        for name in possible_names:
            manual_path = os.path.join(search_path, name)
            if os.path.isfile(manual_path):
                # Determinar mimetype basado en extensión
                if name.endswith('.pdf'):
                    mimetype = 'application/pdf'
                elif name.endswith('.docx'):
                    mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                else:
                    mimetype = 'application/octet-stream'
                
                return send_file(
                    manual_path,
                    mimetype=mimetype,
                    as_attachment=True,
                    download_name='manual_de_uso.pdf' if name.endswith('.pdf') else 'manual_de_uso.docx'
                )
    
    # Si no se encuentra, devolver error
    logger.warning("Manual de uso no encontrado")
    return "Manual de uso no disponible", 404

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(DOCUMENTS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error descargando archivo: {e}")
        return "Error al descargar el archivo", 404

@app.route('/plantilla/<tipo>')
def plantilla(tipo):
    fname = 'plantillas_excel/PlantillaCausa.xlsx' if tipo == 'causa' else 'plantillas_excel/PlantillaObjetivo.xlsx' if tipo == 'objetivo' else None
    if not fname: return "Tipo inválido", 400
    path = os.path.join(BASE_DIR, fname)
    if not os.path.isfile(path): return "Plantilla no encontrada", 404
    return send_from_directory(BASE_DIR, fname, as_attachment=True)

# ---------- Upload + validación + parse + JSON ----------
@app.route('/api/upload_formulario', methods=['POST'])
def upload_formulario():
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "Archivo no recibido"}), 400
    f = request.files['file']
    tipo = (request.form.get('tipo') or '').strip().lower()
    if tipo != 'plantilla':
        return jsonify({"ok": False, "error": "Solo se acepta el tipo 'plantilla'"}), 400

    # Extensión
    original_name = f.filename or ''
    if not original_name.lower().endswith('.xlsx'):
        return jsonify({"ok": False, "error_code": "not_xlsx", "error": "El archivo debe ser un Excel .xlsx."}), 400

    # Guardar archivo
    data = f.read()
    proyecto = session.get('responses', {}).get('nombre_proyecto', 'proyecto')
    slug = re.sub(r'[^A-Za-z0-9_\-]+', '_', proyecto).strip('_') or 'proyecto'
    
    responses = session.get('responses', {})
    previews_md = []
    json_files = []
    
    # Procesar plantilla general
    filename = f"plantilla-{slug}.xlsx"
    save_path = os.path.join(FORMULARIOS_DIR, filename)
    with open(save_path, 'wb') as out:
        out.write(data)
    
    responses["upload_plantilla"] = filename
    session['responses'] = responses
    
    # Procesar plantilla general (sin división entre causas y objetivos)
    try:
        # La función process_uploaded_excel procesa toda la plantilla (causas y objetivos juntos)
        info = process_uploaded_excel('plantilla', save_path, FORMULARIOS_JSON_DIR)
        
        # El árbol contiene todas las hojas procesadas con causas y objetivos
        trees = info.get("tree", {})
        
        # NO guardar los árboles completos en la sesión (son muy grandes para cookies)
        # Solo guardar referencias a los archivos JSON que ya se guardaron en disco
        json_path = info.get("json_path")
        if json_path:
            json_rel = os.path.relpath(json_path, app.static_folder).replace('\\','/')
            json_files.append(json_rel)
            
            # Guardar solo la referencia al archivo JSON en la sesión (no los árboles completos)
            # Los árboles se cargarán desde el archivo JSON cuando se necesiten
            session['plantilla_json_path'] = json_path
            session['causas_json_path'] = json_path  # Para compatibilidad
            session['objetivos_json_path'] = json_path  # Para compatibilidad
        
        preview_md = info.get("preview_md", "")
        if preview_md:
            previews_md.append(preview_md)
        
        return jsonify({
            "ok": True,
            "filename": filename,
            "json_files": json_files,
            "preview_md": "\n\n".join(previews_md) if previews_md else "✅ Plantilla procesada correctamente."
        })
    except Exception as e:
        logger.exception("Error procesando plantilla general")
        return jsonify({"ok": False, "error_code": "parse_error", "error": f"Error al procesar la plantilla: {str(e)}"}), 400

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
    if step_key == 'upload_plantilla':
        return ("📄 **Cargar plantilla.**\n\n"
                "1. Descargue la plantilla en la parte superior del chat.\n"
                "2. Seleccione la **PlantillaIDEC-IA.xlsx**.\n"
                "3. Diligénciela con los árboles de problemas, objetivos, productos e indicadores.\n"
                "4. Súbala en el recuadro que aparece debajo.\n\n")
    return ""

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
        # Si es elige_vertical, mostrar multiselección
        if session['current_step'] == 'elige_vertical':
            return jsonify({
                "response": step['prompt'] + "\n\nSelecciona una o más opciones y pulsa **Confirmar**.",
                "current_step": "elige_vertical",
                "format": "markdown",
                "multiselect": {
                    "items": [
                        "IDEC",
                        "IA"
                    ],
                    "submit_text": "Confirmar"
                }
            })
        payload = {"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"}
        if "options" in step: payload["options"] = step["options"]
        return jsonify(payload)

    # Reanudar del chat libre
    if session.pop('resume_from_alt', False) or user_lower in ('continuar flujo', 'volver al flujo'):
        step_key = session.get('current_step', 'intro_bienvenida')
        step_conf = conversation_flow.get(step_key, {})
        resp_text = step_conf.get("prompt", "…")

        if step_key == 'elige_vertical':
            step = conversation_flow['elige_vertical']
            return jsonify({
                "response": step['prompt'] + "\n\nSelecciona una o más opciones y pulsa **Confirmar**.",
                "current_step": "elige_vertical",
                "format": "markdown",
                "multiselect": {
                    "items": [
                        "IDEC",
                        "IA"
                    ],
                    "submit_text": "Confirmar"
                }
            })

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

        if step_key == 'upload_plantilla':
            resp_text = _upload_prompt_with_link(step_key)
            return jsonify({
                "response": resp_text, "current_step": step_key, "format": "markdown",
                "upload": {"expect_upload": True, "tipo": "plantilla", "download_url": url_for('download_templates')}
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
            # Si es elige_vertical, mostrar multiselección
            if session['current_step'] == 'elige_vertical':
                return jsonify({
                    "response": step['prompt'] + "\n\nSelecciona una o más opciones y pulsa **Confirmar**.",
                    "current_step": "elige_vertical",
                    "format": "markdown",
                    "multiselect": {
                        "items": [
                            "IDEC",
                            "IA"
                        ],
                        "submit_text": "Confirmar"
                    }
                })
            payload = {"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"}
            if "options" in step: payload["options"] = step["options"]
            return jsonify(payload)
        elif _is_no(user_lower):
            session['after_alt_next_step'] = "elige_vertical"
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
        return jsonify({
            "response": step['prompt'] + "\n\nSelecciona una o más opciones y pulsa **Confirmar**.",
            "current_step": "elige_vertical",
            "format": "markdown",
            "multiselect": {
                "items": [
                    "IDEC",
                    "IA"
                ],
                "submit_text": "Confirmar"
            }
        })

    # Elegir vertical (multiselección)
    if current_step == 'elige_vertical':
        if user_message.startswith('__msel__:'):
            raw = user_message.split(':', 1)[1]
            selected = [v.strip() for v in raw.split('|') if v.strip()]
            
            if not selected:
                session['current_step'] = 'finalizado'
                msg = "❌ Este asistente solo atiende proyectos **IDEC/IA**. Se cierra la conversación. Usa *Reiniciar* para empezar de nuevo."
                return jsonify({"response": msg, "current_step": "finalizado", "format": "markdown"})
            
            # Normalizar las selecciones
            has_idec = any('idec' in s.lower() for s in selected)
            has_ia = any('ia' in s.lower() or 'inteligencia artificial' in s.lower() for s in selected)
            
            # Guardar las verticales seleccionadas
            verticales = []
            if has_idec:
                verticales.append('IDEC')
            if has_ia:
                verticales.append('IA')
            responses['vertical'] = ' y '.join(verticales) if len(verticales) > 1 else verticales[0] if verticales else 'Ninguna'
            session['responses'] = responses
            
            # Si incluye IDEC, va a seleccionar componentes primero
            if has_idec:
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
            # Si solo IA, va directo a nombre_proyecto
            elif has_ia:
                session['current_step'] = conversation_flow['elige_vertical']['next_step']  # nombre_proyecto
                step = conversation_flow[session['current_step']]
                return jsonify({"response": step['prompt'], "current_step": session['current_step'], "format": "markdown"})
            else:
                session['current_step'] = 'finalizado'
                msg = "❌ Este asistente solo atiende proyectos **IDEC/IA**. Se cierra la conversación. Usa *Reiniciar* para empezar de nuevo."
                return jsonify({"response": msg, "current_step": "finalizado", "format": "markdown"})
        else:
            # Mostrar multiselección
            step = conversation_flow['elige_vertical']
            return jsonify({
                "response": step['prompt'] + "\n\nSelecciona una o más opciones y pulsa **Confirmar**.",
                "current_step": "elige_vertical",
                "format": "markdown",
                "multiselect": {
                    "items": [
                        "IDEC",
                        "IA"
                    ],
                    "submit_text": "Confirmar"
                }
            })

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
    if current_step == 'upload_plantilla':
        step_key = current_step
        required_flag = "upload_plantilla"

        # Solo procesar si el usuario explícitamente intenta continuar (no mensajes vacíos)
        if user_message and user_message.strip() and re.search(r'\b(continuar|siguiente)\b', user_lower):
            if required_flag in session.get('responses', {}):
                # Archivo subido, avanzar al siguiente paso
                next_step = conversation_flow[step_key]['next_step']
                session['current_step'] = next_step
                step_conf = conversation_flow[next_step]
                text = step_conf.get("prompt", "…")
                payload = {"response": text, "current_step": next_step, "format": "markdown"}
                if "options" in step_conf: payload["options"] = step_conf["options"]
                if next_step == 'upload_plantilla':
                    payload["response"] = _upload_prompt_with_link(next_step)
                    payload["upload"] = {"expect_upload": True, "tipo": "plantilla", "download_url": url_for('download_templates')}
                return jsonify(payload)
            else:
                # Usuario intenta continuar sin haber subido el archivo
                text = _upload_prompt_with_link(step_key) + "\n\n> ⚠️ Aún no has subido el archivo. Por favor súbelo y luego escribe **Continuar**."
                return jsonify({
                    "response": text, "current_step": step_key, "format": "markdown",
                    "upload": {"expect_upload": True, "tipo": "plantilla", "download_url": url_for('download_templates')}
                })

        # Si el usuario no ha escrito "continuar" explícitamente, solo mostrar el mensaje básico sin advertencia
        # Esto incluye cuando el usuario llega al paso por primera vez o escribe cualquier otra cosa
        text = _upload_prompt_with_link(step_key)
        return jsonify({
            "response": text, "current_step": step_key, "format": "markdown",
            "upload": {"expect_upload": True, "tipo": "plantilla", "download_url": url_for('download_templates')}
        })

    # Guardar y avanzar (genérico)
    responses[current_step] = user_message
    session['responses'] = responses

    next_step = conversation_flow.get(current_step, {}).get("next_step")
    if (not next_step) or (next_step == "finalizado"):
        session['current_step'] = "finalizado"
        # ---- Generar documento enriquecido con árboles ----
        # Los árboles no están en la sesión (muy grandes para cookies), se cargarán desde JSON
        filepath = generate_project_document(
            responses,
            client=client,
            documents_dir=DOCUMENTS_DIR,
            causas_tree=None,  # Se cargará desde JSON
            objetivos_tree=None,  # Se cargará desde JSON
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
    if next_step == 'upload_plantilla':
        payload["response"] = _upload_prompt_with_link(next_step)
        payload["upload"]  = {"expect_upload": True, "tipo": "plantilla", "download_url": url_for('download_templates')}
    return jsonify(payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
