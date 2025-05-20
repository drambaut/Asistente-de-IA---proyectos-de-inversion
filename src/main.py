import sys
import os

# Agregar el directorio src al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.chatbot import Chatbot
from src.web.app import app

def main():
    # Crear instancia del chatbot
    chatbot = Chatbot()
    
    # Inicializar el chatbot (procesar PDFs)
    chatbot.initialize()
    
    # Iniciar la aplicación web
    app.run(debug=True)

if __name__ == "__main__":
    main() 