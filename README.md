# Asistente de IA para Proyectos de Inversión

Este proyecto implementa un asistente virtual especializado en proyectos de inversión, específicamente enfocado en la temática de Infraestructura de Datos (IDEC). El asistente guía a los usuarios a través de un flujo estructurado para la creación y evaluación de proyectos de inversión.

## Características

- Interfaz web interactiva y amigable
- Flujo guiado para la creación de proyectos de inversión
- Soporte para múltiples componentes IDEC
- Análisis de problemas y objetivos
- Gestión de presupuestos y recursos
- Evaluación de riesgos y sostenibilidad

## Estructura del Proyecto

```
.
├── src/
│   ├── core/           # Componentes principales
│   │   └── chatbot.py  # Lógica del chatbot
│   ├── utils/          # Utilidades
│   │   └── pdf_processor.py  # Procesamiento de PDFs
│   ├── web/           # Componentes web
│   │   ├── app.py     # Aplicación Flask
│   │   └── templates/ # Plantillas HTML
│   └── main.py        # Punto de entrada
├── static/            # Archivos estáticos
│   ├── css/          # Estilos
│   └── js/           # Scripts JavaScript
├── pdfs/             # Documentos PDF
└── requirements.txt  # Dependencias
```

## Requisitos

- Python 3.11.9 o superior
- pip (gestor de paquetes de Python)
- Git

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/drambaut/Asistente-de-IA---proyectos-de-inversion.git
cd Asistente-de-IA---proyectos-de-inversion
```

2. Crear y activar un entorno virtual (opcional pero recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Iniciar la aplicación:
```bash
python src/main.py
```

2. Abrir el navegador y acceder a:
```
http://localhost:5000
```

3. Seguir el flujo guiado del asistente para crear o evaluar proyectos de inversión.

## Flujo de Trabajo

El asistente guía al usuario a través de los siguientes pasos:

1. Confirmación de interés en proyectos IDEC
2. Datos de la Entidad Pública
3. Selección de componentes IDEC
4. Definición del problema
5. Árbol de problemas
6. Población objetivo
7. Objetivos del proyecto
8. Localización
9. Cadena de valor
10. Análisis e indicadores
11. Presupuesto

## Contribución

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contacto

Daniel Felipe Rambaut Lemus - [@drambaut](https://github.com/drambaut)

Link del proyecto: [https://github.com/drambaut/Asistente-de-IA---proyectos-de-inversion](https://github.com/drambaut/Asistente-de-IA---proyectos-de-inversion)