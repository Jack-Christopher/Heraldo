#!/usr/bin/env python3
"""
Prueba la conexión real con Ollama y procesa un texto pequeño.
"""

import sys
import requests

def test_ollama_connection():
    """Prueba la conexión con Ollama."""
    print("=" * 60)
    print("PRUEBA DE CONEXIÓN CON OLLAMA")
    print("=" * 60)
    
    try:
        # Verificar que Ollama está corriendo
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print(f"✗ Ollama no responde correctamente: {response.status_code}")
            return False
        
        models = response.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        
        print(f"✓ Ollama está corriendo")
        print(f"  Modelos disponibles: {', '.join(model_names)}")
        
        # Verificar que phi3:mini está disponible
        if "phi3:mini" in model_names:
            print("  ✓ phi3:mini está disponible")
        else:
            print("  ⚠ phi3:mini no está disponible")
        
        return True
    except requests.exceptions.ConnectionError:
        print("✗ No se pudo conectar con Ollama")
        print("  Asegúrate de que Ollama esté corriendo: ollama serve")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_ollama_process():
    """Prueba procesar un texto pequeño con Ollama."""
    print("\n" + "=" * 60)
    print("PRUEBA DE PROCESAMIENTO CON OLLAMA")
    print("=" * 60)
    
    try:
        from heraldo.processor import OllamaProcessor
        
        processor = OllamaProcessor(model="phi3:mini")
        
        # Texto de prueba pequeño
        test_text = "La inteligencia artificial es una tecnología revolucionaria."
        
        print(f"Procesando texto: '{test_text}'")
        print("Esto puede tardar unos segundos...")
        
        result = processor.process_block(test_text)
        
        if result:
            print(f"✓ Procesamiento exitoso")
            print(f"  Texto original: {test_text}")
            print(f"  Texto procesado: {result[:100]}...")
            return True
        else:
            print("✗ El procesamiento falló")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecuta las pruebas."""
    connection_ok = test_ollama_connection()
    
    if connection_ok:
        process_ok = test_ollama_process()
        return 0 if process_ok else 1
    else:
        print("\n⚠️  No se puede probar el procesamiento sin conexión a Ollama")
        return 1

if __name__ == "__main__":
    sys.exit(main())
