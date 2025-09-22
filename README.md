# Asistente de IA para Proyectos de Inversión

Este proyecto es un asistente de IA que ayuda a construir proyectos de inversión siguiendo la metodología MGA. Utiliza Azure OpenAI (GPT-4o-mini) para generar documentos profesionales basados en la información proporcionada por el usuario.

## Características

- Interfaz de chat intuitiva y amigable
- Guía paso a paso para la construcción de proyectos de inversión
- Generación automática de documentos en formato Word
- Integración con Azure OpenAI (GPT-4o-mini) para contenido profesional
- Diseño responsivo y moderno

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta de Azure OpenAI con API key y deployment configurado

## Instalación Local

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/asistente-proyectos-inversion.git
cd asistente-proyectos-inversion
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar las variables de entorno:
Copiar el archivo `.env.example` del repositorio y rellenar las variables de entorno.:


`AZURE_OPENAI_ENDPOINT`=https://tu-recurso.openai.azure.com        # URL base del recurso en Azure
`AZURE_OPENAI_API_KEY`=tu_api_key_de_azure_openai                  # Llave secreta para autenticar solicitudes
`AZURE_OPENAI_API_VERSION`=2024-05-01-preview                      # Versión de la API que se va a usar
`AZURE_OPENAI_ASSISTANT_ID`=asst_abc123xyz                         # ID único del asistente en Azure OpenAI
`AZURE_OPENAI_DEPLOYMENT_NAME`=gpt-35-turbo                        # Nombre del despliegue del modelo

**Nota**: Reemplaza todos los valores con tus credenciales reales de Azure OpenAI.

## Uso Local

1. Iniciar el servidor:
```bash
python src/main.py
```

2. Abrir el navegador y acceder a:
```
http://localhost:5000
```

## Despliegue en Producción

**Render**:
   - Crear nuevo Web Service
   - Conectar repositorio de GitHub
   - Configurar variables de entorno
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

## Variables de Entorno

- `AZURE_OPENAI_ENDPOINT`: Es la **URL base de tu recurso de Azure OpenAI**, por ejemplo, `https://mi-recurso.openai.azure.com/`.
- `AZURE_OPENAI_API_KEY`: Es la **llave secreta de autenticación** que Azure te entrega al crear el recurso OpenAI.
- `AZURE_OPENAI_API_VERSION`:Es la **versión de la API de Azure OpenAI** que quieres usar, por ejemplo: `2024-05-01-preview`
- `AZURE_OPENAI_ASSISTANT_ID`: Es el **identificador único de un “asistente” en Azure OpenAI**.
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Es el **nombre del despliegue del modelo que configuraste en Azure OpenAI**, por ejemplo: `gpt-35-turbo`.

## Estructura del Proyecto

```
asistente-proyectos-inversion/
├── src/
│   ├── main.py
│   └── web/
│       ├── app.py
│       ├── static/
│       │   ├── documents/
│       │   └── config.json
│       └── templates/
│           └── index.html
├── requirements.txt
├── runtime.txt
├── Procfile
├── .env
└── README.md
```

## Solución de Problemas

### Error de importación del módulo chatbot
Si encuentras errores relacionados con `src.core.chatbot`, puedes comentar esa línea en `src/main.py` ya que no parece estar siendo utilizada en la aplicación web.


### Error de variables de entorno
Si recibes errores sobre variables de entorno no configuradas:
1. Verifica que el archivo `.env` existe en la raíz del proyecto
2. Asegúrate de que las variables `OPENAI_API_KEY` y `OPENAI_API_BASE` estén configuradas
3. Reinicia la aplicación después de crear/modificar el archivo `.env`


## Contacto
Daniel Rambaut - [LinkedIn](https://www.linkedin.com/in/felipe-rambaut/) - rambautlemusdanielfelipe@gmail.com  

Link del Proyecto: [Asistente de IA - Proyectos de Inversión](https://github.com/drambaut/Asistente-de-IA---proyectos-de-inversion)
