#!/usr/bin/env python3
"""
Script para encontrar y probar voces en español latinoamericano con pyttsx3.
"""

import pyttsx3
import os

def list_voices():
    """Lista todas las voces disponibles y muestra las que son en español."""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    print("=" * 60)
    print("VOCES DISPONIBLES EN EL SISTEMA")
    print("=" * 60)
    
    spanish_voices = []
    
    for i, voice in enumerate(voices):
        name = voice.name
        languages = getattr(voice, 'languages', [])
        lang_str = ', '.join(languages) if languages else 'N/A'
        
        # Buscar voces en español
        is_spanish = False
        if languages:
            is_spanish = any('es' in str(lang).lower() or 'spanish' in str(lang).lower() 
                           for lang in languages)
        if not is_spanish:
            # También buscar en el nombre
            is_spanish = 'español' in name.lower() or 'spanish' in name.lower() or 'es_' in name.lower()
        
        if is_spanish:
            spanish_voices.append((i, voice))
            print(f"✓ [{i}] {name}")
            print(f"    ID: {voice.id}")
            print(f"    Lenguajes: {lang_str}")
            print()
        else:
            print(f"  [{i}] {name} ({lang_str})")
    
    print("\n" + "=" * 60)
    print(f"VOCES EN ESPAÑOL ENCONTRADAS: {len(spanish_voices)}")
    print("=" * 60)
    
    return spanish_voices, voices

def test_voice(voice_id, test_text="Hola, este es un texto de prueba en español latinoamericano."):
    """Prueba una voz específica."""
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        if voice_id >= len(voices):
            print(f"Error: ID de voz {voice_id} no válido")
            return False
        
        voice = voices[voice_id]
        engine.setProperty('voice', voice.id)
        engine.setProperty('rate', 150)
        
        output_file = f'test_voice_{voice_id}.wav'
        print(f"\nProbando voz: {voice.name}")
        print(f"Generando audio en: {output_file}")
        
        engine.save_to_file(test_text, output_file)
        engine.runAndWait()
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✓ Audio generado: {size} bytes")
            print(f"  Archivo: {os.path.abspath(output_file)}")
            return True
        else:
            print("✗ No se generó el archivo")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal."""
    print("\n" + "=" * 60)
    print("BÚSQUEDA DE VOCES EN ESPAÑOL LATINOAMERICANO")
    print("=" * 60)
    
    # Listar voces
    spanish_voices, all_voices = list_voices()
    
    if not spanish_voices:
        print("\n⚠ No se encontraron voces en español explícitamente.")
        print("Probando voces que podrían ser en español...")
        
        # Buscar por patrones comunes
        possible_spanish = []
        for i, voice in enumerate(all_voices):
            name_lower = voice.name.lower()
            if any(pattern in name_lower for pattern in ['es', 'lat', 'mex', 'arg', 'col', 'chile']):
                possible_spanish.append((i, voice))
        
        if possible_spanish:
            print(f"\nVoces posibles en español encontradas: {len(possible_spanish)}")
            for i, voice in possible_spanish:
                print(f"  [{i}] {voice.name}")
            spanish_voices = possible_spanish
    
    if spanish_voices:
        print("\n" + "=" * 60)
        print("PROBANDO VOCES EN ESPAÑOL")
        print("=" * 60)
        
        test_text = "Hola, este es un texto de prueba en español latinoamericano. " \
                   "Queremos verificar que la voz suene natural y clara."
        
        for voice_id, voice in spanish_voices:
            print(f"\n{'='*60}")
            result = test_voice(voice_id, test_text)
            if result:
                print(f"\n✓ Voz {voice_id} ({voice.name}) funciona correctamente")
                print(f"\nPara usar esta voz, configura: --voice {voice_id}")
            else:
                print(f"\n✗ Voz {voice_id} ({voice.name}) no funcionó")
    else:
        print("\n⚠ No se encontraron voces en español.")
        print("Probando con la voz predeterminada...")
        test_voice(0, "Hola, este es un texto de prueba en español.")
    
    print("\n" + "=" * 60)
    print("PRUEBA COMPLETADA")
    print("=" * 60)
    print("\nArchivos de prueba generados. Escúchalos para verificar la calidad.")
    print("Limpia los archivos de prueba con: rm test_voice_*.wav")

if __name__ == "__main__":
    main()
