#!/usr/bin/env python3
"""
Prueba todos los motores TTS (texto-a-audio) implementados en Heraldo.
Genera archivos de audio de prueba para cada motor disponible.
"""

import argparse
import os
import sys
from typing import Optional

# Asegurar que el paquete heraldo sea importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from heraldo.tts_engine import create_tts_engine

# Texto de prueba corto en español
TEST_TEXT = (
    "Hola. Este es un texto de prueba para verificar que todos los motores "
    "de síntesis de voz funcionen correctamente."
)

OUTPUT_DIR = "test_tts_output"

# Configuración por motor (parámetros opcionales para creación)
ENGINE_CONFIG = {
    "piper": {"lang": "es"},
    "gtts": {"lang": "es"},
    "xtts": {"lang": "es", "use_cuda": True},
}


def test_engine(engine_name: str, voice: Optional[str] = None) -> tuple:
    """
    Prueba un motor TTS: disponibilidad y síntesis.

    Returns:
        (éxito, ruta_archivo_generado o None)
    """
    engine_name_lower = engine_name.lower()
    output_file = os.path.join(OUTPUT_DIR, f"{engine_name_lower}.wav")

    try:
        kwargs = ENGINE_CONFIG.get(engine_name_lower, {}).copy()
        if voice:
            kwargs["voice"] = voice
        engine = create_tts_engine(engine_name_lower, **kwargs)

        if not engine.is_available():
            return False, None

        success = engine.synthesize(TEST_TEXT, output_file)
        if success and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            return True, output_file
        return False, None

    except Exception as e:
        print(f"    Error: {e}")
        return False, None


def main():
    parser = argparse.ArgumentParser(
        description="Prueba todos los motores TTS de Heraldo"
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=["piper", "gtts", "xtts", "all"],
        default="all",
        help="Motor a probar (default: all)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help=(
            "Voz específica. Piper: modelo (ej. es_MX-ald-medium) o ruta .onnx. "
            "XTTS/Chatterbox: ruta a WAV de referencia."
        ),
    )
    parser.add_argument(
        "--no-cuda",
        action="store_true",
        help="Forzar CPU para XTTS y Chatterbox (evitar OOM)",
    )
    args = parser.parse_args()

    if args.no_cuda:
        ENGINE_CONFIG["xtts"]["use_cuda"] = False

    engines_to_test = ["piper", "gtts", "xtts"]
    if args.engine != "all":
        engines_to_test = [args.engine]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("PRUEBA DE MOTORES TTS (TEXTO A AUDIO) - HERALDO")
    print("=" * 70)
    print(f"\nTexto de prueba: {TEST_TEXT[:60]}...")
    print(f"Salida: {os.path.abspath(OUTPUT_DIR)}")
    print()

    results = []
    for engine_name in engines_to_test:
        print(f"Probando {engine_name.upper()}...", end=" ")
        ok, path = test_engine(engine_name, args.voice)
        status = "✓ OK" if ok else "✗ FALLO"
        print(status)
        if ok and path:
            size = os.path.getsize(path)
            print(f"    Archivo: {path} ({size // 1024} KB)")
        results.append((engine_name, ok, path))

    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    ok_count = sum(1 for _, ok, _ in results if ok)
    print(f"\nExitosos: {ok_count}/{len(results)}")

    if ok_count > 0:
        print("\nArchivos generados:")
        for name, ok, path in results:
            if ok and path:
                print(f"  - {path}")

    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print("\nMotores que fallaron o no están disponibles:")
        for name in failed:
            hints = {
                "piper": "Instala piper-bin y descarga un modelo .onnx de https://huggingface.co/rhasspy/piper-voices",
                "gtts": "Requiere internet; instala: pip install gtts",
                "xtts": "Instala: pip install coqui-tts; requiere ~2GB; usa --no-cuda si OOM",
            }
            print(f"  - {name}: {hints.get(name, '')}")

    print()
    print("Ejemplo de uso con Heraldo:")
    print("  python -m heraldo.main --pdf archivo.pdf --tts-engine piper --voice es_MX-ald-medium")
    print("  python -m heraldo.main --pdf archivo.pdf --tts-engine gtts")
    print("  python -m heraldo.main --pdf archivo.pdf --tts-engine gtts")
    print("=" * 70)

    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
