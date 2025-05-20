from typing import List, Dict
from openai import OpenAI
from pdf_processor import PDFProcessor
import os
from dotenv import load_dotenv

class Chatbot:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pdf_processor = PDFProcessor()
        self.conversation_history: List[Dict[str, str]] = []

    def initialize(self):
        """Inicializa el chatbot procesando los PDFs disponibles."""
        print("Inicializando el chatbot...")
        self.pdf_processor.process_pdfs()
        print("Chatbot inicializado y listo para usar.")

    def get_response(self, user_input: str) -> str:
        """Obtiene una respuesta del chatbot basada en el input del usuario."""
        # Buscar información relevante en los PDFs
        relevant_chunks = self.pdf_processor.search_similar_chunks(user_input)
        
        # Construir el contexto con la información relevante
        context = "\n".join(relevant_chunks)
        
        # Preparar el mensaje para ChatGPT
        messages = [
            {"role": "system", "content": "Eres un asistente útil que puede responder preguntas basadas en el conocimiento general y en documentos específicos proporcionados."},
            {"role": "system", "content": f"Información relevante de los documentos: {context}"}
        ]
        
        # Añadir el historial de conversación
        messages.extend(self.conversation_history)
        
        # Añadir la pregunta actual del usuario
        messages.append({"role": "user", "content": user_input})
        
        # Obtener respuesta de ChatGPT
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        # Obtener la respuesta
        assistant_response = response.choices[0].message.content
        
        # Actualizar el historial de conversación
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Mantener solo las últimas 10 interacciones para no sobrecargar el contexto
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return assistant_response

    def clear_history(self):
        """Limpia el historial de conversación."""
        self.conversation_history = [] 