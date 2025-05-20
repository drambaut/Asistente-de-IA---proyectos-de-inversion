from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Estado de la conversación
conversation_state = {
    'current_step': 'initial',
    'data': {}
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # Lógica del flujo de conversación
    if conversation_state['current_step'] == 'initial':
        if user_message.lower() in ['si', 'sí', 'yes']:
            conversation_state['current_step'] = 'entity_data'
            return jsonify({
                'response': 'Por favor, ingrese los datos de la entidad pública:\n\nNombre de la Entidad:',
                'next_step': 'entity_name'
            })
        elif user_message.lower() in ['no', 'n']:
            return jsonify({
                'response': 'Entendido. Si desea crear un plan de inversión en el futuro, estaremos aquí para ayudarle.',
                'next_step': 'end'
            })
        else:
            return jsonify({
                'response': '¿Desea construir un plan de Inversión asociado a temática de Infraestructura de datos (IDEC)?\nPor favor, responda con "Sí" o "No".',
                'next_step': 'initial'
            })
    
    elif conversation_state['current_step'] == 'entity_data':
        if conversation_state['data'].get('next_step') == 'entity_name':
            conversation_state['data']['entity_name'] = user_message
            conversation_state['data']['next_step'] = 'entity_sector'
            return jsonify({
                'response': 'Nombre del sector al que está asociado la Entidad:',
                'next_step': 'entity_sector'
            })
        elif conversation_state['data'].get('next_step') == 'entity_sector':
            conversation_state['data']['entity_sector'] = user_message
            conversation_state['current_step'] = 'idec_components'
            return jsonify({
                'response': '''Seleccione los componentes IDEC que desea incluir (puede seleccionar múltiples, separados por comas):
1. Gobernanza de datos
2. Interoperabilidad
3. Herramientas técnicas y tecnológicas
4. Seguridad y privacidad de datos
5. Datos
6. Aprovechamiento de datos''',
                'next_step': 'idec_components'
            })

    # Aquí se pueden agregar más pasos del flujo según sea necesario
    
    return jsonify({
        'response': 'Lo siento, ha ocurrido un error. Por favor, intente de nuevo.',
        'next_step': 'error'
    })

if __name__ == '__main__':
    app.run(debug=True) 