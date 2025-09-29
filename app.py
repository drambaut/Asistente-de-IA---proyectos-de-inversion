# app.py - Chatbot MGA/IDEC/IA ejecutable con frontend en index.html

from flask import Flask, render_template, request, jsonify, session, send_from_directory, url_for
from flask_cors import CORS
import os
import traceback
import logging
from dotenv import load_dotenv
from docx import Document
from openai import AzureOpenAI
import json
import time
import httpx

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'idec_secret_key_change_in_production')

DOCUMENTS_DIR = os.path.join(app.static_folder, 'documents')
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
    http_client=httpx.Client(verify=False)
)

# ============================================================================
# Helper: pedir Markdown y reintentar si la respuesta se corta por tokens
# ============================================================================
def ask_markdown_azure(messages, *, model_name=None, max_tokens=1500, temperature=0.4, max_rounds=3):
    """
    Devuelve SIEMPRE Markdown (texto plano) y, si el modelo se corta por tokens,
    hace rondas de 'continúa' hasta completar o llegar a max_rounds.
    """
    full_text = ""
    rounds = 0
    _messages = list(messages)  # copia para ir acumulando

    # Resuelve nombre del deployment/modelo desde env si no llega
    model_name = model_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    while rounds < max_rounds:
        rounds += 1
        resp = client.chat.completions.create(
            model=model_name,
            messages=_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        chunk = (choice.message.content or "").strip()
        full_text += chunk

        finish = getattr(choice, "finish_reason", None)

        # Si no se cortó, salimos
        if finish not in ("length", "content_filter"):
            break

        # Si se cortó por longitud, pedimos continuación
        _messages = _messages + [
            {"role": "assistant", "content": chunk},
            {"role": "user", "content": "Por favor continúa exactamente donde te quedaste."}
        ]

    return full_text

# ============================================================================
# Generar documento Word a partir de las respuestas del flujo
# ============================================================================
def generate_project_document(responses: dict, filename: str = None) -> str:
    if not filename:
        filename = f"proyecto_inversion_{int(time.time())}.docx"

    filepath = os.path.join(DOCUMENTS_DIR, filename)

    prompt = (
        "Eres un experto en formulación de proyectos bajo la Metodología General Ajustada (MGA) "
        "del DNP de Colombia. Con la siguiente información recolectada del usuario, organiza un "
        "documento estructurado como un proyecto de inversión en Infraestructura de Datos o IA.\n\n"
        "El documento debe estar en español, redactado en tono técnico y formal, con estilo claro.\n"
        "Usa títulos y subtítulos en el formato Markdown (#, ##, ###).\n"
        "Secciones mínimas:\n"
        "- Introducción\n"
        "- Problema central\n"
        "- Causas y efectos (directos e indirectos)\n"
        "- Población afectada\n"
        "- Población objetivo\n"
        "- Localización\n"
        "- Objetivo central\n"
        "- Medios y fines (directos e indirectos)\n"
        "- Cadena de valor\n"
        "- Conclusión\n\n"
        f"Información recolectada: {json.dumps(responses, indent=2, ensure_ascii=False)}\n\n"
        "Redacta el documento con títulos y subtítulos claros, listados cuando corresponda y párrafos bien organizados."
    )

    completion = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "Eres un asistente experto en proyectos MGA/IDEC/IA. Responde en Markdown."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2500,
        temperature=0.5
    )

    text = completion.choices[0].message.content.strip()

    doc = Document()
    doc.add_heading("Proyecto de Inversión en IDEC/IA", level=0)

    # Interpretar títulos Markdown y párrafos
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("### "):
            doc.add_heading(line.replace("### ", ""), level=3)
        elif line.startswith("## "):
            doc.add_heading(line.replace("## ", ""), level=2)
        elif line.startswith("# "):
            doc.add_heading(line.replace("# ", ""), level=1)
        else:
            doc.add_paragraph(line)

    doc.save(filepath)
    return filepath

# ============================================================================
# Rutas básicas
# ============================================================================
@app.route('/')
def index():
    session.clear()
    session['current_step'] = 'intro_bienvenida'
    session['responses'] = {}
    session['mode'] = 'flow'  # default: flujo normal
    return render_template('index.html')

@app.route('/config.json')
def serve_config():
    config = {
        'api_endpoint': '/api/chat',
        'description': 'Asistente para formulación de proyectos MGA/IDEC/IA'
    }
    return jsonify(config)

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(DOCUMENTS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error descargando archivo: {str(e)}")
        return "Error al descargar el archivo", 404

@app.route('/reset', methods=['POST'])
def reset_conversation():
    session.clear()
    session['current_step'] = 'intro_bienvenida'
    session['responses'] = {}
    session['mode'] = 'flow'
    return jsonify({"status": "ok", "message": "Conversación reiniciada"})

# ============================================================================
# CHAT LIBRE (IA)
# ============================================================================
@app.route('/api/chat_alt', methods=['POST'])
def chat_alt():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()

        # Entramos a modo chat libre
        session['mode'] = "alt"

        # Palabra para volver al flujo normal
        if user_message.strip().lower() == "finalizar":
            session['mode'] = "flow"
            return jsonify({
                "response": "✅ Has finalizado el chat libre. Volvemos al flujo normal.",
                "options": ["Continuar flujo"],
                "format": "markdown"
            })

        # Prompt de sistema que EXIGE Markdown
        system_msg = {
            "role": "system",
            "content": (
                "Eres un asistente experto en proyectos TIC del gobierno colombiano. "
                "RESPONDE SIEMPRE en Markdown válido: usa encabezados con #, ##, ###; "
                "negritas con **texto**; listas con -, 1. 2.; bloques de código con ```; "
                "no uses HTML."
            )
        }
        user_msg = {"role": "user", "content": user_message}

        md = ask_markdown_azure(
            [system_msg, user_msg],
            model_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            max_tokens=1500,     # espacio para respuestas largas
            temperature=0.4,     # más estable
            max_rounds=3         # continúa si se corta por tokens
        )

        return jsonify({"response": md, "format": "markdown"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================
conversation_flow = {
    "intro_bienvenida": {
        "prompt": "👋 ¡Hola! Soy tu asistente virtual para ayudarte en la formulación de proyectos de inversión relacionados con Infraestructura de Datos (IDEC) o Inteligencia Artificial (IA). Vamos a empezar paso a paso.\n\nTe acompañaré paso a paso para estructurar tu proyecto conforme a la Metodología General Ajustada (MGA) del Departamento Nacional de Planeación.\n\n🧰 Te haré preguntas clave para estructurar el proyecto.\n\n❓ ¿Tienes dudas generales antes de empezar?",
        "options": [
            "Sí, entiendo el proceso y deseo continuar",
            "No del todo, me gustaría una breve explicación",
            "Tengo dudas puntuales sobre los lineamientos del Plan Nacional de Infraestructura de Datos (PNID) o del CONPES 4144 de Inteligencia Artificial"
        ],
        "next_step": "pregunta_1_ciclo"
    },
    "pregunta_1_ciclo": {
        "prompt": "¿Conoces el ciclo de inversión pública y las fases que lo componen?",
        "options": ["Sí, lo conozco", "No, me gustaría entenderlo mejor"],
        "next_step": "pregunta_2_herramienta"
    },
    "explicacion_ciclo": {
        "prompt": "📘 El ciclo de inversión pública incluye:\n• Identificación del problema\n• Formulación\n• Evaluación\n• Registro en BPIN\n• Implementación y seguimiento",
        "next_step": "pregunta_2_herramienta"
    },
    "pregunta_2_herramienta": {
        "prompt": "¿Tienes claro en qué parte del proceso se aplica esta herramienta?",
        "options": ["Sí, etapa de formulación", "No, no lo tengo claro"],
        "next_step": "pregunta_3_entidad"
    },
    "pregunta_3_entidad": {
        "prompt": "🏢 ¿Cuál es el nombre de tu entidad?",
        "next_step": "pregunta_4_sector"
    },
    "pregunta_4_sector": {
        "prompt": "🗂️ ¿A qué sector administrativo pertenece tu entidad?",
        "options": ["Sector Educación", "Sector Salud", "Sector TIC", "Otro"],
        "next_step": "pregunta_5_rol"
    },
    "pregunta_5_rol": {
        "prompt": "👤 ¿Cuál es tu rol dentro de la entidad?",
        "options": ["Responsable de planeación", "Profesional técnico", "Coordinador TIC", "Otro"],
        "next_step": "pregunta_6_tipo_proyecto"
    },
    "pregunta_6_tipo_proyecto": {
        "prompt": "🎯 ¿Qué tipo de proyecto deseas formular?",
        "options": ["Infraestructura", "Fortalecimiento institucional", "Soluciones tecnológicas", "Piloto de innovación"],
        "next_step": "problema_central"
    },
    "problema_central": {
        "prompt": "🎯 ¿Cuál es la problemática principal que tu proyecto busca atender?",
        "next_step": "objetivo_central"
    },
    "objetivo_central": {
        "prompt": "📌 ¿Cuál es el objetivo central del proyecto?",
        "next_step": "cadena_valor"
    },
    "cadena_valor": {
        "prompt": "🔗 ¿Cómo se constituye tu cadena de valor?",
        "next_step": "finalizado"
    }
}

@app.route('/api/chat', methods=['POST'])
def chat():
    # Si estamos en modo alternativo, delegamos a chat_alt
    if session.get("mode") == "alt":
        return chat_alt()

    data = request.get_json()
    user_message = data.get('message', '').strip()
    user_lower = user_message.lower()

    current_step = session.get('current_step', 'intro_bienvenida')
    responses = session.get('responses', {})

    # inicio
    if current_step == 'intro_bienvenida' and user_lower in ['iniciar', 'start']:
        intro = conversation_flow['intro_bienvenida']
        session['current_step'] = 'intro_bienvenida'
        return jsonify({
            "response": intro['prompt'],
            "current_step": "intro_bienvenida",
            "options": intro['options']
        })

    # guardar respuesta
    responses[current_step] = user_message
    session['responses'] = responses

    # avanzar flujo
    next_step = conversation_flow.get(current_step, {}).get("next_step")

    # 'finalizado' es estado terminal (o ausencia de next_step)
    if (not next_step) or (next_step == "finalizado"):
        session['current_step'] = "finalizado"

        filepath = generate_project_document(responses)
        filename = os.path.basename(filepath)
        download_url = url_for('download_file', filename=filename)

        return jsonify({
            "response": (
                "✅ Flujo completado. Documento generado. "
                f"<a href='{download_url}' target='_blank'>Descargar documento</a>"
            ),
            "current_step": "finalizado"
        })

    # Caso normal: continuar al siguiente paso definido en el flujo
    session['current_step'] = next_step
    step_conf = conversation_flow.get(next_step, {})
    payload = {
        "response": step_conf.get("prompt", "…"),
        "current_step": next_step
    }
    if "options" in step_conf:
        payload["options"] = step_conf["options"]
    return jsonify(payload)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
