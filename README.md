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
Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:
```
# Configuración de Azure OpenAI
OPENAI_API_KEY=tu_api_key_de_azure_openai
OPENAI_API_BASE=https://tu-instancia.openai.azure.com

# Clave secreta para Flask (cambiar en producción)
SECRET_KEY=tu_clave_secreta_aqui
```

**Nota**: Reemplaza `tu_api_key_de_azure_openai` y `https://tu-instancia.openai.azure.com` con tus credenciales reales de Azure OpenAI.

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

### Opción 1: Despliegue Simple (Heroku, Railway, Render)

1. **Heroku**:
   ```bash
   # Instalar Heroku CLI
   heroku create tu-app-name
   heroku config:set OPENAI_API_KEY=tu_api_key
   heroku config:set SECRET_KEY=tu_clave_secreta
   git push heroku main
   ```

2. **Railway**:
   - Conectar tu repositorio de GitHub
   - Configurar variables de entorno en el dashboard
   - El despliegue será automático

3. **Render**:
   - Crear nuevo Web Service
   - Conectar repositorio de GitHub
   - Configurar variables de entorno
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`

### Opción 2: Docker

1. **Construir y ejecutar con Docker**:
   ```bash
   # Construir la imagen
   docker build -t asistente-ia .
   
   # Ejecutar el contenedor
   docker run -p 8000:8000 -e OPENAI_API_KEY=tu_api_key asistente-ia
   ```

2. **Usar Docker Compose**:
   ```bash
   # Crear archivo .env con las variables
   echo "OPENAI_API_KEY=tu_api_key" > .env
   echo "SECRET_KEY=tu_clave_secreta" >> .env
   
   # Ejecutar con docker-compose
   docker-compose up -d
   ```

### Opción 3: VPS con Docker

1. **En tu servidor**:
   ```bash
   # Clonar el repositorio
   git clone https://github.com/tu-usuario/asistente-proyectos-inversion.git
   cd asistente-proyectos-inversion
   
   # Configurar variables de entorno
   nano .env
   
   # Ejecutar con docker-compose
   docker-compose up -d
   ```

2. **Configurar Nginx** (opcional):
   ```nginx
   server {
       listen 80;
       server_name tu-dominio.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Variables de Entorno

- `OPENAI_API_KEY`: Tu clave de API de Azure OpenAI (requerida)
- `OPENAI_API_BASE`: URL base de tu instancia de Azure OpenAI (requerida)
- `SECRET_KEY`: Clave secreta para las sesiones de Flask (recomendada para producción)

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
├── wsgi.py
├── Procfile
├── Dockerfile
├── docker-compose.yml
├── .env
└── README.md
```

## Solución de Problemas

### Error de importación del módulo chatbot
Si encuentras errores relacionados con `src.core.chatbot`, puedes comentar esa línea en `src/main.py` ya que no parece estar siendo utilizada en la aplicación web.

### Error de permisos en Docker
Asegúrate de que el directorio `src/web/static/documents` tenga los permisos correctos:
```bash
chmod 755 src/web/static/documents
```

### Error de variables de entorno
Si recibes errores sobre variables de entorno no configuradas:
1. Verifica que el archivo `.env` existe en la raíz del proyecto
2. Asegúrate de que las variables `OPENAI_API_KEY` y `OPENAI_API_BASE` estén configuradas
3. Reinicia la aplicación después de crear/modificar el archivo `.env`

## Contribuir

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contacto

Tu Nombre - [@tutwitter](https://twitter.com/tutwitter) - email@ejemplo.com

Link del Proyecto: [https://github.com/tu-usuario/asistente-proyectos-inversion](https://github.com/tu-usuario/asistente-proyectos-inversion)