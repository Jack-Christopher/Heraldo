#!/usr/bin/env python3
"""
Script de prueba para la API de DeepSeek.
Comprueba DEEPSEEK_API_KEY y hace una llamada de prueba sin ejecutar el pipeline completo.

Uso (desde la raíz del proyecto):
  python scripts/test_deepseek_api.py
  python -m scripts.test_deepseek_api
"""

import os
import sys

# Raíz del proyecto para importar heraldo
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Cargar .env desde la raíz del proyecto
try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv no está instalado. Ejecuta: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

load_dotenv(os.path.join(root_dir, ".env"))

API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY or not API_KEY.strip():
    print("Error: DEEPSEEK_API_KEY no está definido.", file=sys.stderr)
    print("Copia .env.example a .env y configura DEEPSEEK_API_KEY con tu token.", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests no está instalado. Ejecuta: pip install requests", file=sys.stderr)
    sys.exit(1)

from heraldo.utils import parse_deepseek_response

url = "https://api.deepseek.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": "Responde en una sola frase: ¿Cuál es la capital de Francia?"},
    ],
    "max_tokens": 100,
}

print("Enviando petición de prueba a la API de DeepSeek...")
try:
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    ok, content, error_message = parse_deepseek_response(r)
    if ok:
        if content:
            print("Respuesta:", content)
            print("OK: La API de DeepSeek responde correctamente.")
        else:
            print("Advertencia: La API respondió OK pero el contenido está vacío.", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error API DeepSeek: {error_message}", file=sys.stderr)
        sys.exit(1)
except requests.exceptions.Timeout:
    print("Error: Timeout al conectar con la API de DeepSeek.", file=sys.stderr)
    sys.exit(1)
except requests.exceptions.RequestException as e:
    err_msg = str(e)
    if hasattr(e, "response") and e.response is not None:
        err_msg = parse_deepseek_response(e.response)[2] or err_msg
    print(f"Error de conexión: {err_msg}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
