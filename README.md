# Asistente de IA para Proyectos de Inversión

Este proyecto es un asistente de IA que ayuda a construir proyectos de inversión siguiendo la metodología MGA. Utiliza ChatGPT para generar documentos profesionales basados en la información proporcionada por el usuario.

## Características

- Interfaz de chat intuitiva y amigable
- Guía paso a paso para la construcción de proyectos de inversión
- Generación automática de documentos en formato Word
- Integración con ChatGPT para contenido profesional
- Diseño responsivo y moderno

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta de OpenAI con API key

## Instalación

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
OPENAI_API_KEY=tu_api_key_aqui
```

## Uso

1. Iniciar el servidor:
```bash
python src/web/app.py
```

2. Abrir el navegador y acceder a:
```
http://localhost:5000
```

3. Seguir las instrucciones del asistente para construir tu proyecto de inversión.

## Estructura del Proyecto

```
asistente-proyectos-inversion/
├── src/
│   └── web/
│       ├── app.py
│       ├── static/
│       │   ├── documents/
│       │   └── config.json
│       └── templates/
│           └── index.html
├── requirements.txt
├── .env
└── README.md
```

## Despliegue en GitHub Pages

Para desplegar el proyecto en GitHub Pages:

1. Crear un nuevo repositorio en GitHub
2. Subir el código al repositorio:
```bash
git init
git add .
git commit -m "Primer commit"
git remote add origin https://github.com/tu-usuario/asistente-proyectos-inversion.git
git push -u origin main
```

3. En la configuración del repositorio en GitHub:
   - Ir a "Settings" > "Pages"
   - Seleccionar la rama "main" como fuente
   - Guardar los cambios

4. El sitio estará disponible en:
```
https://tu-usuario.github.io/asistente-proyectos-inversion
```

## Contribuir

Las contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contacto

Tu Nombre - [@tutwitter](https://twitter.com/tutwitter) - email@ejemplo.com

Link del Proyecto: [https://github.com/tu-usuario/asistente-proyectos-inversion](https://github.com/tu-usuario/asistente-proyectos-inversion)