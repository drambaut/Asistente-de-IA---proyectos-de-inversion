from flask import Flask, render_template, request, jsonify, session, send_from_directory, url_for
from flask_cors import CORS
import os
from datetime import datetime
import logging
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import openai
from dotenv import load_dotenv
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)  # Cambiar a INFO para producción
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)  # Habilitar CORS para todos los endpoints

# Configurar clave secreta desde variable de entorno o usar una por defecto
app.secret_key = os.getenv('SECRET_KEY', 'idec_secret_key_change_in_production')

# Asegurarse de que el directorio de documentos existe
DOCUMENTS_DIR = os.path.join(app.static_folder, 'documents')
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Configurar OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Definir el flujo de la conversación
conversation_flow = {
    'entidad_nombre': {
        'prompt': 'Por favor, ingrese el nombre de la entidad pública:',
        'next_step': 'entidad_sector'
    },
    'entidad_sector': {
        'prompt': 'Por favor, ingrese el sector al que pertenece la entidad:',
        'next_step': 'componentes_idec'
    },
    'componentes_idec': {
        'prompt': 'Seleccione los componentes IDEC que desea incluir en su proyecto (puede seleccionar varios):',
        'options': [
            'Gobernanza de datos',
            'Interoperabilidad',
            'Herramientas técnicas y tecnológicas',
            'Seguridad y privacidad de datos',
            'Datos',
            'Aprovechamiento de datos'
        ],
        'min_selections': 1,
        'next_step': 'problema_descripcion'
    },
    'problema_descripcion': {
        'prompt': 'Describa la problemática o oportunidad que su proyecto busca atender (máximo 500 caracteres):',
        'next_step': 'situacion_actual'
    },
    'situacion_actual': {
        'prompt': 'Describa la situación actual de la problemática (máximo 500 caracteres):',
        'next_step': 'causas_efectos'
    },
    'causas_efectos': {
        'prompt': 'Liste las causas y efectos de la problemática (máximo 500 caracteres):',
        'next_step': 'poblacion_afectada'
    },
    'poblacion_afectada': {
        'prompt': 'Describa la población afectada (cantidad y tipo de población, máximo 300 caracteres):',
        'next_step': 'objetivo_general'
    },
    'objetivo_general': {
        'prompt': 'Describa el objetivo general del proyecto (máximo 300 caracteres):',
        'next_step': 'objetivos_especificos'
    },
    'objetivos_especificos': {
        'prompt': 'Describa los objetivos específicos del proyecto (máximo 500 caracteres):',
        'next_step': 'localizacion'
    },
    'localizacion': {
        'prompt': 'Describa la localización del proyecto (territorial, nacional, departamental, etc., máximo 300 caracteres):',
        'next_step': 'cadena_valor'
    },
    'cadena_valor': {
        'prompt': 'Describa la cadena de valor del proyecto (máximo 500 caracteres):',
        'next_step': 'riesgos'
    },
    'riesgos': {
        'prompt': 'Liste y describa los riesgos identificados (máximo 500 caracteres):',
        'next_step': 'sostenibilidad'
    },
    'sostenibilidad': {
        'prompt': 'Describa la estrategia de sostenibilidad (máximo 500 caracteres):',
        'next_step': 'presupuesto_general'
    },
    'presupuesto_general': {
        'prompt': 'Describa el presupuesto general del proyecto (máximo 500 caracteres):',
        'next_step': 'presupuesto_detalle'
    },
    'presupuesto_detalle': {
        'prompt': 'Describa el detalle del presupuesto por actividad (máximo 500 caracteres):',
        'next_step': 'end'
    }
}

@app.route('/')
def index():
    # Inicializar la sesión
    session.clear()
    session['current_step'] = 'initial'
    session['responses'] = {}
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip().lower()
        current_step = session.get('current_step', 'initial')
        
        logger.debug(f"Paso actual: {current_step}, Mensaje: {user_message}")
        
        # Paso inicial
        if current_step == 'initial':
            # Lista de respuestas afirmativas
            respuestas_afirmativas = [
                'si', 'sí', 'claro', 'de acuerdo', 'correcto', 'ok', 'okay', 
                'por supuesto', 'afirmativo', 'adelante', 'continuar', 'proceder',
                'empecemos', 'vamos', 'comencemos', 'iniciar', 'comenzar',
                'listo', 'preparado', 'listo estoy', 'estoy listo', 'listo para empezar',
                'quiero', 'deseo', 'me gustaría', 'quiero empezar', 'deseo empezar',
                'me gustaría empezar', 'quiero continuar', 'deseo continuar',
                'me gustaría continuar', 'quiero proceder', 'deseo proceder',
                'me gustaría proceder', 'quiero iniciar', 'deseo iniciar',
                'me gustaría iniciar', 'quiero comenzar', 'deseo comenzar',
                'me gustaría comenzar', 'quiero seguir', 'deseo seguir',
                'me gustaría seguir', 'quiero avanzar', 'deseo avanzar',
                'me gustaría avanzar', 'quiero proseguir', 'deseo proseguir',
                'me gustaría proseguir', 'quiero seguir adelante', 'deseo seguir adelante',
                'me gustaría seguir adelante', 'quiero continuar adelante', 'deseo continuar adelante',
                'me gustaría continuar adelante', 'quiero proceder adelante', 'deseo proceder adelante',
                'me gustaría proceder adelante', 'quiero iniciar adelante', 'deseo iniciar adelante',
                'me gustaría iniciar adelante', 'quiero comenzar adelante', 'deseo comenzar adelante',
                'me gustaría comenzar adelante', 'quiero seguir adelante', 'deseo seguir adelante',
                'me gustaría seguir adelante', 'quiero avanzar adelante', 'deseo avanzar adelante',
                'me gustaría avanzar adelante', 'quiero proseguir adelante', 'deseo proseguir adelante',
                'me gustaría proseguir adelante'
            ]
            
            if user_message in respuestas_afirmativas:
                session['current_step'] = 'entidad_nombre'
                return jsonify({
                    'response': 'Por favor, ingrese el nombre de la entidad pública:',
                    'current_step': 'entidad_nombre'
                })
            else:
                return jsonify({
                    'response': 'Entendido. Si en el futuro desea construir un plan de inversión, no dude en contactarnos.',
                    'current_step': 'end'
                })

        # Almacenar la respuesta actual
        session['responses'] = session.get('responses', {})
        session['responses'][current_step] = user_message

        # Obtener el siguiente paso
        next_step = conversation_flow[current_step]['next_step']
        session['current_step'] = next_step

        # Si es el paso final, generar el documento
        if next_step == 'end':
            try:
                # Generar el documento usando ChatGPT
                document_content = generate_document_with_gpt(session['responses'])
                filename = save_document(document_content)
                download_url = url_for('download_file', filename=filename)
                
                return jsonify({
                    'response': f'¡Gracias por proporcionar toda la información! Su documento ha sido generado. <a href="{download_url}" class="download-link">Descargar Documento</a>',
                    'current_step': 'end',
                    'download_url': download_url
                })
            except Exception as e:
                logger.error(f"Error generando documento: {str(e)}")
                return jsonify({
                    'response': 'Lo siento, ha ocurrido un error al generar el documento. Por favor, intente nuevamente.',
                    'current_step': 'end'
                })

        return jsonify({
            'response': conversation_flow[next_step]['prompt'],
            'current_step': next_step
        })

    except Exception as e:
        logger.error(f"Error en chat: {str(e)}")
        return jsonify({
            'response': 'Lo siento, ha ocurrido un error inesperado. Por favor, intente nuevamente.',
            'current_step': 'end'
        })

def generate_document_with_gpt(responses):
    try:
        # Crear el prompt para ChatGPT
        prompt = f"""
        Por favor, genera un documento de proyecto de inversión basado en la siguiente información:

        Entidad: {responses.get('entidad_nombre', '')}
        Sector: {responses.get('entidad_sector', '')}
        Componentes IDEC: {responses.get('componentes_idec', '')}
        Problemática: {responses.get('problema_descripcion', '')}
        Situación Actual: {responses.get('situacion_actual', '')}
        Causas y Efectos: {responses.get('causas_efectos', '')}
        Población Afectada: {responses.get('poblacion_afectada', '')}
        Objetivo General: {responses.get('objetivo_general', '')}
        Objetivos Específicos: {responses.get('objetivos_especificos', '')}
        Localización: {responses.get('localizacion', '')}
        Cadena de Valor: {responses.get('cadena_valor', '')}
        Riesgos: {responses.get('riesgos', '')}
        Sostenibilidad: {responses.get('sostenibilidad', '')}
        Presupuesto General: {responses.get('presupuesto_general', '')}
        Presupuesto Detalle: {responses.get('presupuesto_detalle', '')}

        Por favor, genera un documento profesional y bien estructurado que incluya:
        1. Resumen ejecutivo
        2. Información de la entidad
        3. Descripción del problema y situación actual
        4. Objetivos y población objetivo
        5. Localización y cadena de valor
        6. Análisis de riesgos
        7. Estrategia de sostenibilidad
        8. Presupuesto y detalles financieros
        """

        # Llamar a la API de ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en redacción de proyectos de inversión."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error generando documento con GPT: {str(e)}")
        raise

def save_document(content):
    try:
        # Crear un nuevo documento
        doc = Document()
        
        # Agregar título
        title = doc.add_heading('Propuesta de Proyecto de Inversión', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Agregar contenido
        doc.add_paragraph(content)
        
        # Guardar el documento
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'proyecto_inversion_{timestamp}.docx'
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        doc.save(filepath)
        
        return filename

    except Exception as e:
        logger.error(f"Error guardando documento: {str(e)}")
        raise

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(DOCUMENTS_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error descargando archivo: {str(e)}")
        return "Error al descargar el archivo", 404

@app.route('/config.json')
def serve_config():
    try:
        config_path = os.path.join(app.static_folder, 'config.json')
        return send_from_directory(app.static_folder, 'config.json')
    except Exception as e:
        logger.error(f"Error sirviendo config.json: {str(e)}")
        return jsonify({'error': 'Configuración no disponible'}), 404

# Generar archivo de configuración para GitHub Pages
def generate_github_pages_config():
    config = {
        'conversation_flow': conversation_flow,
        'api_endpoint': '/api/chat'
    }
    
    # Crear el archivo en la carpeta static del directorio actual
    config_path = os.path.join(app.static_folder, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

if __name__ == '__main__':
    generate_github_pages_config()
    app.run(host='0.0.0.0', port=5001, debug=True) 