#!/usr/bin/env python3
"""
Script de verificación de instalación para Heraldo.
Verifica todas las dependencias y componentes necesarios.
"""

import sys
import subprocess
import os

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def check_python_package(package_name, import_name=None):
    """Verifica si un paquete Python está instalado."""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} instalado")
        return True
    except ImportError:
        print(f"✗ {package_name} NO instalado")
        return False

def check_command(command, args=["--version"], timeout=5):
    """Verifica si un comando del sistema está disponible."""
    try:
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            timeout=timeout
        )
        if result.returncode == 0:
            output = result.stdout.decode().strip()
            print(f"✓ {command} instalado: {output[:80]}")
            return True
        else:
            print(f"✗ {command} instalado pero no funciona correctamente")
            return False
    except FileNotFoundError:
        print(f"✗ {command} NO instalado o no en PATH")
        return False
    except subprocess.TimeoutExpired:
        print(f"✗ {command} timeout al verificar")
        return False
    except Exception as e:
        print(f"✗ {command} error: {e}")
        return False

def main():
    print_header("VERIFICACIÓN DE INSTALACIÓN - HERALDO")
    
    results = {
        "python_packages": [],
        "system_commands": [],
        "tts_engines": [],
        "ollama": False,
        "nltk_data": False
    }
    
    # 1. Verificar paquetes Python básicos
    print_header("1. PAQUETES PYTHON BÁSICOS")
    
    packages = [
        ("pdfplumber", "pdfplumber"),
        ("tiktoken", "tiktoken"),
        ("nltk", "nltk"),
        ("requests", "requests"),
        ("tqdm", "tqdm"),
        ("gtts", "gtts"),
        ("pyttsx3", "pyttsx3"),
    ]
    
    for pkg_name, import_name in packages:
        result = check_python_package(pkg_name, import_name)
        results["python_packages"].append((pkg_name, result))
    
    # 2. Verificar datos de NLTK
    print_header("2. DATOS DE NLTK")
    try:
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
            print("✓ NLTK punkt data instalado")
            results["nltk_data"] = True
        except LookupError:
            print("✗ NLTK punkt data NO instalado")
            print("  Ejecuta: python -m nltk.downloader punkt")
            results["nltk_data"] = False
    except ImportError:
        print("✗ NLTK no está instalado")
        results["nltk_data"] = False
    
    # 3. Verificar Ollama
    print_header("3. OLLAMA")
    ollama_installed = check_command("ollama", ["--version"])
    results["ollama"] = ollama_installed
    
    if ollama_installed:
        # Verificar modelos disponibles
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.returncode == 0:
                models = result.stdout.strip()
                if models and "NAME" in models:
                    print(f"\n  Modelos disponibles:")
                    for line in models.split('\n')[1:]:  # Skip header
                        if line.strip():
                            print(f"    - {line.strip()}")
                else:
                    print("  ⚠ No hay modelos descargados")
                    print("  Ejecuta: ollama pull llama3.1:8b")
        except Exception as e:
            print(f"  ⚠ No se pudo listar modelos: {e}")
    
    # 4. Verificar motores TTS
    print_header("4. MOTORES TTS")
    
    # Piper TTS
    print("\n4.1. Piper TTS:")
    piper_installed = check_command("piper-bin", ["--version"])
    results["tts_engines"].append(("piper", piper_installed))
    
    if piper_installed:
        # Verificar variable de entorno
        piper_path = os.environ.get("PIPER_PATH")
        piper_voice = os.environ.get("PIPER_VOICE")
        if piper_path:
            print(f"  PIPER_PATH configurado: {piper_path}")
        if piper_voice:
            print(f"  PIPER_VOICE configurado: {piper_voice}")
        else:
            print("  ⚠ PIPER_VOICE no configurado (usa --voice en el comando)")
    
    # gTTS
    print("\n4.2. Google TTS (gTTS):")
    gtts_installed = check_python_package("gtts", "gtts")
    results["tts_engines"].append(("gtts", gtts_installed))
    
    # pyttsx3
    print("\n4.3. pyttsx3:")
    pyttsx3_installed = check_python_package("pyttsx3", "pyttsx3")
    if pyttsx3_installed:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            print(f"  ✓ pyttsx3 funcionando, {len(voices)} voces disponibles")
            if voices:
                print(f"    Voz predeterminada: {voices[0].name if voices else 'N/A'}")
        except Exception as e:
            print(f"  ✗ pyttsx3 instalado pero no funciona: {e}")
            pyttsx3_installed = False
    results["tts_engines"].append(("pyttsx3", pyttsx3_installed))
    
    # 5. Verificar ffmpeg (opcional, para gTTS)
    print_header("5. HERRAMIENTAS ADICIONALES")
    ffmpeg_installed = check_command("ffmpeg", ["-version"])
    if not ffmpeg_installed:
        print("  ⚠ ffmpeg no instalado (opcional, solo necesario para convertir MP3 a WAV con gTTS)")
    
    # 6. Verificar PyTorch (opcional)
    print("\n6. PyTorch (opcional, para limpieza de memoria GPU):")
    torch_installed = check_python_package("torch", "torch")
    if torch_installed:
        try:
            import torch
            if torch.cuda.is_available():
                print(f"  ✓ CUDA disponible: {torch.cuda.get_device_name(0)}")
            else:
                print("  ⚠ PyTorch instalado pero CUDA no disponible (modo CPU)")
        except Exception as e:
            print(f"  ⚠ Error al verificar CUDA: {e}")
    
    # 7. Verificar estructura del proyecto
    print_header("7. ESTRUCTURA DEL PROYECTO")
    required_files = [
        "heraldo/__init__.py",
        "heraldo/main.py",
        "heraldo/extractor.py",
        "heraldo/processor.py",
        "heraldo/consolidator.py",
        "heraldo/tts_engine.py",
        "heraldo/checkpoint.py",
        "heraldo/utils.py",
        "requirements.txt",
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} NO existe")
            all_files_exist = False
    
    # Resumen final
    print_header("RESUMEN")
    
    python_ok = all(r[1] for r in results["python_packages"])
    tts_ok = any(r[1] for r in results["tts_engines"])
    
    print(f"Paquetes Python: {'✓ OK' if python_ok else '✗ FALTANTES'}")
    print(f"Datos NLTK: {'✓ OK' if results['nltk_data'] else '✗ FALTANTES'}")
    print(f"Ollama: {'✓ OK' if results['ollama'] else '✗ FALTANTE'}")
    print(f"Motores TTS: {'✓ OK' if tts_ok else '✗ FALTANTES'}")
    print(f"Estructura proyecto: {'✓ OK' if all_files_exist else '✗ FALTANTES'}")
    
    if python_ok and results['nltk_data'] and results['ollama'] and tts_ok and all_files_exist:
        print("\n🎉 ¡Todo está listo para usar Heraldo!")
    else:
        print("\n⚠️  Hay componentes faltantes. Revisa los errores arriba.")
    
    return results

if __name__ == "__main__":
    main()
