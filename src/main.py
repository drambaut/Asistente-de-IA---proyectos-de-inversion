import sys
import os

# Agregar el directorio src al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from src.core.chatbot import Chatbot  # Comentado porque el módulo no existe
from src.web.app import app

def main():
    # Crear instancia del chatbot (comentado porque no existe)
    # chatbot = Chatbot()
    
    # Inicializar el chatbot (procesar PDFs) - comentado
    # chatbot.initialize()
    
    # Iniciar la aplicación web
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main() 