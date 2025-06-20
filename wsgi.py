import os
import sys

# Agregar el directorio src al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.web.app import app

if __name__ == "__main__":
    app.run() 