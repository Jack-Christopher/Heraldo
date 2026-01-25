#!/usr/bin/env python3
"""
Script mejorado para encontrar y probar voces en español latinoamericano.
Prueba diferentes configuraciones y busca modelos de Piper TTS.
"""

import pyttsx3
import os
import subprocess

def test_pyttsx3_voices():
    """Prueba todas las voces de pyttsx3 y busca las mejores para español."""
    print("=" * 60)
    print("PRUEBA DE VOCES PYTTSX3")
    print("=" * 60)
    
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # Buscar voces que puedan ser mejores
    test_text = "Hola, este es un texto de prueba en español latinoamericano. " \
               "Queremos una voz natural y clara sin acento extranjero."
    
    spanish_voices = []
    for i, voice in enumerate(voices):
        name_lower = voice.name.lower()
        id_lower = str(voice.id).lower()
        
        # Buscar voces en español
        if 'spanish' in name_lower or 'español' in name_lower or 'es' in id_lower:
            spanish_voices.append((i, voice))
    
    print(f"\nVoces en español encontradas: {len(spanish_voices)}")
    
    # Probar cada voz
    results = []
    for voice_id, voice in spanish_voices:
        try:
            engine = pyttsx3.init()
            engine.setProperty('voice', voice.id)
            engine.setProperty('rate', 150)
            
            output_file = f'test_voice_{voice_id}.wav'
            engine.save_to_file(test_text, output_file)
            engine.runAndWait()
            
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                results.append({
                    'id': voice_id,
                    'name': voice.name,
                    'voice_id': voice.id,
                    'file': output_file,
                    'size': size
                })
                print(f"✓ [{voice_id}] {voice.name} - {size} bytes")
        except Exception as e:
            print(f"✗ [{voice_id}] {voice.name} - Error: {e}")
    
    return results

def check_piper_spanish_models():
    """Verifica si hay modelos de Piper TTS en español disponibles."""
    print("\n" + "=" * 60)
    print("VERIFICANDO PIPER TTS - MODELOS EN ESPAÑOL")
    print("=" * 60)
    
    # Modelos comunes de Piper en español latinoamericano
    spanish_models = [
        "es_ES-davefx-medium",  # España
        "es_ES-shared-medium",  # España
        "es_MX-ald-medium",     # México
        "es_MX-claude-medium",  # México
        "es_AR-tango-medium",   # Argentina
        "es_CO-carlfm-medium",  # Colombia
        "es_CL-catalina-medium", # Chile
    ]
    
    print("\nModelos de Piper TTS en español disponibles:")
    print("(Necesitas descargarlos desde HuggingFace)")
    print("\nURLs para descargar:")
    print("https://huggingface.co/rhasspy/piper-voices/tree/main/es")
    
    for model in spanish_models:
        print(f"\n  - {model}")
        print(f"    https://huggingface.co/rhasspy/piper-voices/resolve/main/es/{model.split('-')[0]}/{model.split('-')[1]}/medium/{model}.onnx")
        print(f"    https://huggingface.co/rhasspy/piper-voices/resolve/main/es/{model.split('-')[0]}/{model.split('-')[1]}/medium/{model}.onnx.json")
    
    # Verificar si piper-bin está disponible
    try:
        result = subprocess.run(['piper-bin', '--version'], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print("\n✓ piper-bin está disponible")
            return True
    except:
        pass
    
    print("\n⚠ piper-bin no está disponible o no está en PATH")
    return False

def test_piper_model(model_name, test_text):
    """Prueba un modelo específico de Piper."""
    print(f"\nProbando modelo: {model_name}")
    
    # Buscar el modelo en ubicaciones comunes
    possible_paths = [
        f"{model_name}.onnx",
        f"~/.local/share/piper/voices/{model_name}/{model_name}.onnx",
        f"./models/{model_name}.onnx",
    ]
    
    model_path = None
    for path in possible_paths:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            model_path = expanded
            break
    
    if not model_path:
        print(f"⚠ Modelo {model_name} no encontrado")
        print(f"  Descarga desde: https://huggingface.co/rhasspy/piper-voices")
        return False
    
    try:
        output_file = f"test_piper_{model_name.replace('/', '_')}.wav"
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
        
        stdout, stderr = process.communicate(input=test_text, timeout=30)
        
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
        return False

def main():
    """Función principal."""
    print("\n" + "=" * 60)
    print("BÚSQUEDA MEJORADA DE VOCES EN ESPAÑOL LATINOAMERICANO")
    print("=" * 60)
    
    test_text = "Hola, este es un texto de prueba en español latinoamericano. " \
               "Queremos verificar que la voz suene natural y clara, " \
               "sin acento extranjero o imperialista."
    
    # Probar voces de pyttsx3
    pyttsx3_results = test_pyttsx3_voices()
    
    # Verificar Piper TTS
    piper_available = check_piper_spanish_models()
    
    print("\n" + "=" * 60)
    print("RECOMENDACIONES")
    print("=" * 60)
    
    if pyttsx3_results:
        print("\nVoces de pyttsx3 probadas:")
        for r in pyttsx3_results:
            print(f"  [{r['id']}] {r['name']} - {r['file']}")
        print("\n⚠ Nota: pyttsx3 usa voces sintéticas básicas que pueden sonar robóticas.")
        print("  Para mejor calidad, considera usar Piper TTS con modelos específicos.")
    
    if piper_available:
        print("\n✓ Piper TTS está disponible")
        print("\nPara mejor calidad de voz en español latinoamericano:")
        print("1. Descarga un modelo de Piper desde HuggingFace:")
        print("   - es_MX-ald-medium (México)")
        print("   - es_AR-tango-medium (Argentina)")
        print("   - es_CO-carlfm-medium (Colombia)")
        print("\n2. Usa el modelo con:")
        print("   python -m heraldo.main --pdf archivo.pdf --tts-engine piper --voice /ruta/al/modelo.onnx")
    
    print("\n" + "=" * 60)
    print("ARCHIVOS DE PRUEBA GENERADOS")
    print("=" * 60)
    print("Escucha los archivos test_voice_*.wav para comparar.")
    print("Limpia con: rm test_voice_*.wav test_piper_*.wav")

if __name__ == "__main__":
    main()
