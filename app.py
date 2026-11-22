import os
import sys
from pathlib import Path

# Point d'entrée à la racine du projet
ROOT_DIR = Path(__file__).resolve().parent
CINEJOY_DIR = ROOT_DIR / "cinejoy_app"

if str(CINEJOY_DIR) not in sys.path:
    sys.path.insert(0, str(CINEJOY_DIR))

# On se place dans le dossier cinejoy_app
os.chdir(str(CINEJOY_DIR))

# Exécution du serveur Flask cinejoy_app
script_path = CINEJOY_DIR / "app.py"
with open(script_path, "r", encoding="utf-8") as f:
    code = compile(f.read(), str(script_path), "exec")
    exec(code, {"__name__": "__main__", "__file__": str(script_path)})
