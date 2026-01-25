#!/usr/bin/env python3
"""
Script para descargar y probar modelos de Piper TTS en español latinoamericano.
"""

import os
import subprocess
import requests
from pathlib import Path

def download_piper_model(model_name, output_dir="models"):
    """
    Descarga un modelo de Piper TTS desde HuggingFace.
    
    Args:
        model_name: Nombre del modelo (ej: es_MX-ald-medium)
        output_dir: Directorio donde guardar el modelo
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Construir URLs
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es"
    
    # Extraer país y voz del nombre del modelo
    # Formato: es_MX-ald-medium -> es_MX/ald/medium
    parts = model_name.split('-')
    country = parts[0]  # es_MX
    voice_name = parts[1]  # ald
    quality = parts[2]  # medium
    
    model_url = f"{base_url}/{country}/{voice_name}/{quality}/{model_name}.onnx"
    json_url = f"{base_url}/{country}/{voice_name}/{quality}/{model_name}.onnx.json"
    
    model_path = os.path.join(output_dir, f"{model_name}.onnx")
    json_path = os.path.join(output_dir, f"{model_name}.onnx.json")
    
    print(f"\nDescargando modelo: {model_name}")
    print(f"Desde: {model_url}")
    
    # Descargar modelo .onnx
    if not os.path.exists(model_path):
        try:
            print("Descargando archivo .onnx...")
            response = requests.get(model_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r  Progreso: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            print("\n✓ Modelo descargado")
        except Exception as e:
            print(f"\n✗ Error al descargar modelo: {e}")
            return None
    else:
        print("✓ Modelo ya existe")
    
    # Descargar archivo .json
    if not os.path.exists(json_path):
        try:
            print("Descargando archivo .json...")
            response = requests.get(json_url, timeout=60)
            response.raise_for_status()
            with open(json_path, 'wb') as f:
                f.write(response.content)
            print("✓ JSON descargado")
        except Exception as e:
            print(f"⚠ Error al descargar JSON (opcional): {e}")
    
    return model_path if os.path.exists(model_path) else None

def test_piper_model(model_path, test_text):
    """Prueba un modelo de Piper con un texto."""
    if not model_path or not os.path.exists(model_path):
        print("✗ Modelo no encontrado")
        return False
    
    output_file = "test_piper_spanish.wav"
    
    try:
        print(f"\nProbando modelo: {os.path.basename(model_path)}")
        print(f"Texto: {test_text[:50]}...")
        
        cmd = [
            'piper-bin',
            '--model', model_path,
            '--output_file', output_file
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=test_text, timeout=60)
        
        if process.returncode == 0 and os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✓ Audio generado: {size} bytes")
            print(f"  Archivo: {os.path.abspath(output_file)}")
            return True
        else:
            print(f"✗ Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal."""
    print("=" * 60)
    print("PRUEBA DE MODELOS PIPER TTS EN ESPAÑOL LATINOAMERICANO")
    print("=" * 60)
    
    # Modelos disponibles en español latinoamericano
    models = {
        "México": "es_MX-ald-medium",
        "Argentina": "es_AR-tango-medium",
        "Colombia": "es_CO-carlfm-medium",
        "Chile": "es_CL-catalina-medium",
    }
    
    print("\nModelos disponibles:")
    for country, model in models.items():
        print(f"  - {country}: {model}")
    
    # Probar con el modelo de México primero (generalmente más neutral)
    test_model = "es_MX-ald-medium"
    test_text = "Hola, este es un texto de prueba en español latinoamericano. " \
               "Queremos verificar que la voz suene natural y clara, " \
               "sin acento extranjero o imperialista."
    
    print(f"\n{'='*60}")
    print(f"Probando modelo: {test_model} (México)")
    print(f"{'='*60}")
    
    # Descargar modelo
    model_path = download_piper_model(test_model)
    
    if model_path:
        # Probar el modelo
        success = test_piper_model(model_path, test_text)
        
        if success:
            print(f"\n{'='*60}")
            print("✓ PRUEBA EXITOSA")
            print(f"{'='*60}")
            print(f"\nArchivo de prueba generado: test_piper_spanish.wav")
            print(f"Escucha el archivo para verificar la calidad de la voz.")
            print(f"\nSi te gusta esta voz, podemos configurarla como predeterminada.")
            print(f"\nPara usar este modelo:")
            print(f"  python -m heraldo.main --pdf archivo.pdf --tts-engine piper --voice {model_path}")
        else:
            print("\n✗ No se pudo generar el audio")
    else:
        print("\n✗ No se pudo descargar el modelo")
        print("\nPuedes descargarlo manualmente desde:")
        print("https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/ald/medium")

if __name__ == "__main__":
    main()
