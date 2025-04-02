# Chatbot con ChatGPT y Documentos PDF

Este proyecto implementa un chatbot que puede responder preguntas utilizando tanto el conocimiento general de ChatGPT como información específica de documentos PDF.

## Requisitos

- Python 3.8 o superior
- API key de OpenAI

## Instalación

1. Clona este repositorio
2. Instala las dependencias:
```bash
pip install -r requirements.txt
```
3. Crea un archivo `.env` en la raíz del proyecto y añade tu API key de OpenAI:
```
OPENAI_API_KEY=tu_api_key_aquí
```

## Uso

1. Coloca tus documentos PDF en la carpeta `pdfs/`
2. Ejecuta el script principal:
```bash
python main.py
```

## Estructura del Proyecto

- `main.py`: Script principal que ejecuta el chatbot
- `pdf_processor.py`: Módulo para procesar documentos PDF
- `chatbot.py`: Implementación del chatbot
- `pdfs/`: Carpeta para almacenar los documentos PDF
- `.env`: Archivo para las variables de entorno (no incluido en el repositorio)