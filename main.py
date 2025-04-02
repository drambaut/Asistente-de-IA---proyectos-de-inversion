from chatbot import Chatbot

def main():
    # Crear instancia del chatbot
    chatbot = Chatbot()
    
    # Inicializar el chatbot (procesar PDFs)
    chatbot.initialize()
    
    print("\n¡Bienvenido al Chatbot con ChatGPT y Documentos PDF!")
    print("Escribe 'salir' para terminar la conversación.")
    print("Escribe 'limpiar' para limpiar el historial de conversación.")
    
    while True:
        # Obtener input del usuario
        user_input = input("\nTú: ").strip()
        
        # Verificar comandos especiales
        if user_input.lower() == 'salir':
            print("\n¡Hasta luego!")
            break
        elif user_input.lower() == 'limpiar':
            chatbot.clear_history()
            print("\nHistorial de conversación limpiado.")
            continue
        
        # Obtener y mostrar la respuesta
        try:
            response = chatbot.get_response(user_input)
            print("\nAsistente:", response)
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Por favor, intenta de nuevo.")

if __name__ == "__main__":
    main() 