# app.py - Chatbot MGA/IDEC/IA ejecutable con frontend en index.html

from flask import Flask, render_template, request, jsonify, session, send_from_directory, url_for
from flask_cors import CORS
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openai import AzureOpenAI
import json
import time

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
    api_key=os.getenv('OPENAI_API_KEY'),
    api_version=os.getenv('OPENAI_API_VERSION', '2024-02-15-preview'),
    azure_endpoint=os.getenv('OPENAI_API_BASE')
)
ASSISTANT_ID = os.getenv('ASSISTANT_ID')

if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY no está configurada")
if not os.getenv('OPENAI_API_BASE'):
    raise ValueError("OPENAI_API_BASE no está configurada")
if not ASSISTANT_ID:
    raise ValueError("ASSISTANT_ID no está configurado")

@app.route('/')
def index():
    session.clear()
    session['current_step'] = 'intro_bienvenida'
    session['responses'] = {}
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

# --- FLUJO DE CONVERSACIÓN COMPLETO ---
conversation_flow = {
    "intro_bienvenida": {
        "prompt": "👋 ¡Hola! Soy tu asistente virtual para ayudarte en la formulación de proyectos de inversión relacionados con Infraestructura de Datos (IDEC) o Inteligencia Artificial (IA). Vamos a empezar paso a paso.\n\nTe acompañaré paso a paso para estructurar tu proyecto conforme a la Metodología General Ajustada (MGA) del Departamento Nacional de Planeación, incorporando los enfoques técnicos y estratégicos de las guías de Infraestructura de datos del Estado Colombiano (IDEC) e Inteligencia artificial.\n\n🧰 A lo largo del proceso, te haré preguntas que nos permitirán construir los elementos clave del proyecto: desde la definición del problema, identificación de causas y objetivos (árboles de problema), hasta la justificación, la población beneficiaria, y el desarrollo de objetivos, cadena de valor, indicadores, presupuesto, cronograma y demás componentes técnicos.\n\n❓ ¿Tienes dudas generales antes de empezar?",
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
        "prompt": "📘 No te preocupes. El ciclo de inversión pública incluye las siguientes etapas:\n\n• Identificación del problema u oportunidad de mejora\n• Formulación de alternativas y estructuración técnica y financiera\n• Evaluación y viabilidad del proyecto\n• Registro en el Banco de Programas y Proyectos (BPIN)\n• Implementación, seguimiento y evaluación\n\nPuedes conocer más en la Guía MGA del DNP: https://www.dnp.gov.co/planes-nacionales/metodologia-general-ajustada",
        "next_step": "pregunta_2_herramienta"
    },
    "pregunta_2_herramienta": {
        "prompt": "¿Tienes claro en qué parte del proceso de inversión se aplica esta herramienta?",
        "options": ["Sí, sé que corresponde a la etapa previa de formulación", "No, no lo tengo claro"],
        "next_step": "confirmacion_inicio"
    },
    "explicacion_herramienta": {
        "prompt": "Esta herramienta te será útil especialmente en la etapa previa de formulación del proyecto, donde se definen el problema, los objetivos, las alternativas, los beneficiarios, los costos y los componentes técnicos, alineados con la MGA.",
        "next_step": "confirmacion_inicio"
    },
    "confirmacion_inicio": {
        "prompt": "✅ Gracias. Con esta información ya podemos iniciar el flujo principal para estructurar tu proyecto de inversión en IDEC o IA.",
        "next_step": "pregunta_3_entidad"
    },
    "pregunta_3_entidad": {
        "prompt": "🏢 ¿Cuál es el nombre de tu entidad?",
        "next_step": "pregunta_4_sector"
    },
    "pregunta_4_sector": {
        "prompt": "🗂️ ¿A qué sector administrativo pertenece tu entidad?",
        "options": [
            "Sector Administrativo del Deporte",
            "Sector Agropecuario, Pesquero y de Desarrollo Rural",
            "Sector Ambiente y Desarrollo Sostenible",
            "Sector Ciencia y Tecnología",
            "Sector Cultura",
            "Sector de Comercio, Industria y Turismo",
            "Sector de Igualdad y Equidad",
            "Sector de la Defensa Nacional",
            "Sector de las Tecnologías de la Información y las Comunicaciones",
            "Sector del Interior",
            "Sector del Trabajo",
            "Sector Educación Nacional",
            "Sector Función Pública",
            "Sector Hacienda y Crédito Público",
            "Sector Inteligencia Estratégica y Contrainteligencia",
            "Sector Inclusión Social y Reconciliación",
            "Sector Información Estadística",
            "Sector Justicia y del Derecho",
            "Sector Minas y Energía",
            "Sector Planeación",
            "Sector Presidencia de la República",
            "Sector Relaciones Exteriores",
            "Sector Salud y de la Protección Social",
            "Sector Transporte",
            "Sector Vivienda, Ciudad y Territorio"
        ],
        "next_step": "pregunta_5_rol"
    },
    "pregunta_5_rol": {
        "prompt": "👤 ¿Cuál es tu rol dentro de la entidad?",
        "options": ["Responsable de planeación", "Profesional técnico", "Coordinador TIC o de datos", "Otro"],
        "next_step": "pregunta_6_tipo_proyecto"
    },
    "pregunta_6_tipo_proyecto": {
        "prompt": "🎯 ¿Qué tipo de proyecto de inversión deseas formular?",
        "options": [
            "🏗️ Infraestructura física (por ejemplo: centros de datos, redes, servidores)",
            "📊 Fortalecimiento institucional (por ejemplo: gobernanza, talento humano, procesos)",
            "🤖 Desarrollo o implementación de soluciones tecnológicas",
            "🧪 Proyecto piloto o de innovación",
            "📚 Otro tipo (por favor especifica)"
        ],
        "next_step": "pregunta_6_orientacion"
    },
    "pregunta_6_orientacion": {
        "prompt": "🚀 ¿Deseas construir un proyecto de inversión asociando componentes TIC en temas de IDEC o IA?",
        "options": ["Si en IDEC", "Si en IA", "No - Cierre de la conversación"],
        "next_step": "componentes_idec"
    },
    "componentes_idec": {
        "prompt": "📦 La siguiente es la lista de componentes IDEC. Selecciona los que deseas incluir (puedes escribirlos separados por coma):\n\n• Gobernanza de datos\n• Interoperabilidad\n• Herramientas técnicas y tecnológicas\n• Seguridad y privacidad de datos\n• Datos\n• Aprovechamiento de datos",
        "next_step": "problema_central"
    },
    "componentes_ia": {
        "prompt": "🤖 La siguiente es la lista de componentes de IA. Selecciona los que deseas incluir (puedes escribirlos separados por coma):\n\n• Componente 1: Chipset y Hardware informático\n• Componente 2: Productos y Servicios integrados de IA\n• Componente 3: Entrenamiento y Desarrollo de Modelos de IA\n• Componente 4: Ejecución y Despliegue de Modelos de IA\n• Componente 5: Aplicaciones de IA\n• Componente 6: Servicios de IA\n• Componente 7: Gobernanza de IA",
        "next_step": "problema_central"
    },
    "problema_central": {
        "prompt": "🎯 ¿Cuál es la problemática o la oportunidad que tu proyecto de inversión busca atender o resolver?\n\n(Escribe tu respuesta. Si no tienes claridad escribe: 'No tengo claro')",
        "next_step": "causas_efectos_directos"
    },
    "ayuda_problema_central": {
        "prompt": "🧩 En la identificación del problema es común encontrar múltiples situaciones negativas que afectan a una comunidad. Para reducir la complejidad del análisis, se debe delimitar claramente el ámbito del problema. Si las ideas iniciales son vagas o generales, se recomienda listar las condiciones negativas más relevantes según la comunidad. Luego, se deben priorizar aquellas que estén asociadas con el problema principal. Finalmente, se organiza el listado en secuencias, identificando relaciones de dependencia entre las situaciones negativas.\n\nPor favor, vuelve a formular la problemática principal.",
        "next_step": "problema_central"
    },
    "causas_efectos_directos": {
        "prompt": "📌 ¿Cuáles son las causas y efectos directos de la problemática u oportunidad (mínimo 2)?\n\n(Escribe tu respuesta. Si necesitas ayuda escribe: 'Necesito ayuda')",
        "next_step": "causas_efectos_indirectos"
    },
    "ayuda_causas_efectos_directos": {
        "prompt": "🔎 Las causas directas son las acciones o hechos concretos que dan origen al problema central (primer nivel, debajo del problema). Los efectos directos son consecuencias que genera la situación negativa identificada como problema central (primer nivel, arriba del problema). No existe relación directa causa→efecto; ambas se relacionan con el problema central.\n\nAhora, por favor lista al menos 2 causas directas y 2 efectos directos.",
        "next_step": "causas_efectos_directos"
    },
    "causas_efectos_indirectos": {
        "prompt": "🌐 ¿Cuáles son las causas y efectos indirectos de la problemática u oportunidad (mínimo 1 por cada causa/efecto directo)?\n\n(Escribe tu respuesta. Si necesitas ayuda escribe: 'Necesito ayuda')",
        "next_step": None
    },
    "ayuda_causas_efectos_indirectos": {
        "prompt": "🧠 Las causas indirectas dan origen a las causas directas y se encuentran a partir del segundo nivel (debajo de las causas directas). Los efectos indirectos son situaciones negativas generadas por los efectos directos (niveles superiores a los efectos directos).\n\nAhora, por favor lista al menos 1 causa indirecta por cada causa directa y 1 efecto indirecto por cada efecto directo.",
        "next_step": "causas_efectos_indirectos"
    }
}



# --- AJUSTES EN /api/chat PARA MANEJAR LA RAMA IDEC/IA Y LOS NUEVOS PASOS ---

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    user_lower = user_message.lower()

    current_step = session.get('current_step', 'intro_bienvenida')
    responses = session.get('responses', {})

    # iniciar flujo con la intro
    if current_step == 'intro_bienvenida' and user_lower in ['iniciar', 'start', '']:
        intro_data = conversation_flow['intro_bienvenida']
        session['current_step'] = 'intro_bienvenida'
        return jsonify({
            "response": intro_data['prompt'],
            "current_step": "intro_bienvenida",
            "options": intro_data['options']
        })

    # guardar respuesta
    responses[current_step] = user_message
    session['responses'] = responses

    # INTRO: decidir siguiente
    if current_step == "intro_bienvenida":
        if "entiendo" in user_lower or "continuar" in user_lower:
            next_step = "pregunta_1_ciclo"
        elif "breve" in user_lower or "explicación" in user_lower or "explicacion" in user_lower:
            next_step = "explicacion_ciclo"
        elif "pnid" in user_lower or "conpes" in user_lower or "dudas" in user_lower:
            session['current_step'] = "pregunta_1_ciclo"
            return jsonify({
                "response": "📚 PNID y CONPES 4144 establecen lineamientos clave para proyectos IDEC/IA.\n\n¿Conoces el ciclo de inversión pública?",
                "current_step": "pregunta_1_ciclo",
                "options": conversation_flow["pregunta_1_ciclo"]["options"]
            })
        else:
            return jsonify({
                "response": "Por favor, selecciona una de las opciones disponibles:",
                "current_step": "intro_bienvenida",
                "options": conversation_flow["intro_bienvenida"]["options"]
            })
        session['current_step'] = next_step
        payload = {
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        }
        if "options" in conversation_flow[next_step]:
            payload["options"] = conversation_flow[next_step]["options"]
        return jsonify(payload)

    # P1: ciclo
    if current_step == "pregunta_1_ciclo":
        if user_lower in ["no", "no lo conozco", "no, me gustaría entenderlo mejor", "no, me gustaria entenderlo mejor"]:
            next_step = "explicacion_ciclo"
        elif user_lower in ["sí", "si", "sí lo conozco", "si lo conozco", "sí, lo conozco", "si, lo conozco", "lo conozco"]:
            next_step = conversation_flow[current_step]["next_step"]
        else:
            return jsonify({
                "response": "Por favor selecciona una de las opciones válidas:",
                "current_step": current_step,
                "options": conversation_flow[current_step]["options"]
            })
        session['current_step'] = next_step
        payload = {
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        }
        if "options" in conversation_flow[next_step]:
            payload["options"] = conversation_flow[next_step]["options"]
        return jsonify(payload)

    # Explicación ciclo -> P2
    if current_step == "explicacion_ciclo":
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        payload = {
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        }
        if "options" in conversation_flow[next_step]:
            payload["options"] = conversation_flow[next_step]["options"]
        return jsonify(payload)

    # P2: herramienta
    if current_step == "pregunta_2_herramienta":
        if "no" in user_lower:
            next_step = "explicacion_herramienta"
        else:
            next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        payload = {
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        }
        if "options" in conversation_flow[next_step]:
            payload["options"] = conversation_flow[next_step]["options"]
        return jsonify(payload)

    # Explicación herramienta -> confirmación
    if current_step == "explicacion_herramienta":
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Confirmación -> entidad
    if current_step == "confirmacion_inicio":
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Sector/rol/tipo -> orientación
    if current_step in ["pregunta_3_entidad", "pregunta_4_sector", "pregunta_5_rol", "pregunta_6_tipo_proyecto"]:
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        payload = {
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        }
        if "options" in conversation_flow[next_step]:
            payload["options"] = conversation_flow[next_step]["options"]
        return jsonify(payload)

    # Orientación IDEC/IA
    if current_step == "pregunta_6_orientacion":
        if "idec" in user_lower:
            next_step = "componentes_idec"
        elif user_lower == "si en ia" or " ia" in user_lower or user_lower.startswith("si en ia"):
            next_step = "componentes_ia"
        elif user_lower.startswith("no"):
            session['current_step'] = "finalizado"
            return jsonify({
                "response": "Entendido. Conversación finalizada. ¡Gracias!",
                "current_step": "finalizado"
            })
        else:
            return jsonify({
                "response": "Por favor selecciona una de las opciones válidas:",
                "current_step": "pregunta_6_orientacion",
                "options": conversation_flow["pregunta_6_orientacion"]["options"]
            })
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Componentes IDEC/IA -> problema central
    if current_step in ["componentes_idec", "componentes_ia"]:
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Problema central (texto libre + ayuda)
    if current_step == "problema_central":
        if "no tengo claro" in user_lower or "no tengo claridad" in user_lower:
            next_step = "ayuda_problema_central"
        else:
            next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Ayuda problema central -> vuelve a problema_central
    if current_step == "ayuda_problema_central":
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Causas/Efectos directos (texto + ayuda)
    if current_step == "causas_efectos_directos":
        if "necesito ayuda" in user_lower:
            next_step = "ayuda_causas_efectos_directos"
        else:
            next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Ayuda directos -> vuelve a directos
    if current_step == "ayuda_causas_efectos_directos":
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Causas/Efectos indirectos (texto + ayuda)
    if current_step == "causas_efectos_indirectos":
        if "necesito ayuda" in user_lower:
            next_step = "ayuda_causas_efectos_indirectos"
            session['current_step'] = next_step
            return jsonify({
                "response": conversation_flow[next_step]["prompt"],
                "current_step": next_step
            })
        else:
            # Fin (no hay next_step definido aquí)
            session['current_step'] = "finalizado"
            return jsonify({
                "response": "¡Gracias! Se han registrado causas y efectos indirectos. Puedes continuar con la siguiente sección del proyecto.",
                "current_step": "finalizado"
            })

    # Ayuda indirectos -> vuelve a indirectos
    if current_step == "ayuda_causas_efectos_indirectos":
        next_step = conversation_flow[current_step]["next_step"]
        session['current_step'] = next_step
        return jsonify({
            "response": conversation_flow[next_step]["prompt"],
            "current_step": next_step
        })

    # Fallback genérico
    if current_step in conversation_flow:
        next_step = conversation_flow[current_step].get("next_step")
        if next_step:
            session['current_step'] = next_step
            payload = {
                "response": conversation_flow[next_step]["prompt"],
                "current_step": next_step
            }
            if "options" in conversation_flow[next_step]:
                payload["options"] = conversation_flow[next_step]["options"]
            return jsonify(payload)

    session['current_step'] = "finalizado"
    return jsonify({
        "response": "Flujo completado.",
        "current_step": "finalizado"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)