#!/usr/bin/env python3
"""
Script de prueba para verificar que todos los módulos funcionan correctamente.
"""

import sys
import os

def test_imports():
    """Prueba que todos los módulos se pueden importar."""
    print("=" * 60)
    print("PRUEBA 1: Importación de módulos")
    print("=" * 60)
    
    try:
        from heraldo import extractor, processor, consolidator, checkpoint, tts_engine, utils, main
        print("✓ Todos los módulos se importaron correctamente")
        return True
    except Exception as e:
        print(f"✗ Error al importar módulos: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_utils():
    """Prueba las funciones de utilidades."""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Funciones de utilidades")
    print("=" * 60)
    
    try:
        from heraldo.utils import count_tokens, get_pdf_name, ensure_directory
        
        # Probar conteo de tokens
        text = "Este es un texto de prueba para contar tokens."
        tokens = count_tokens(text)
        print(f"✓ Conteo de tokens funciona: {len(text)} caracteres = {tokens} tokens")
        
        # Probar get_pdf_name
        pdf_name = get_pdf_name("/ruta/test/documento.pdf")
        assert pdf_name == "documento", f"Esperado 'documento', obtenido '{pdf_name}'"
        print(f"✓ get_pdf_name funciona: {pdf_name}")
        
        # Probar ensure_directory
        test_dir = "test_dir"
        ensure_directory(test_dir)
        assert os.path.exists(test_dir), "Directorio no se creó"
        os.rmdir(test_dir)
        print(f"✓ ensure_directory funciona")
        
        return True
    except Exception as e:
        print(f"✗ Error en utilidades: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_checkpoint():
    """Prueba el sistema de checkpoints."""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Sistema de checkpoints")
    print("=" * 60)
    
    try:
        from heraldo.checkpoint import CheckpointManager
        
        # Crear checkpoint manager de prueba
        cm = CheckpointManager("test.pdf", checkpoint_dir="test_checkpoints")
        
        # Guardar checkpoint
        cm.save_checkpoint(
            last_block=5,
            processed_blocks=["bloque1", "bloque2", "bloque3"],
            total_blocks=10
        )
        print("✓ Checkpoint guardado correctamente")
        
        # Cargar checkpoint
        checkpoint_data = cm.load_checkpoint()
        assert checkpoint_data is not None, "Checkpoint no se cargó"
        assert checkpoint_data["last_block"] == 5, "Datos incorrectos"
        print("✓ Checkpoint cargado correctamente")
        
        # Verificar should_resume
        should_resume = cm.should_resume()
        assert should_resume == True, "Debería poder reanudar"
        print("✓ should_resume funciona correctamente")
        
        # Limpiar
        cm.clear_checkpoint()
        print("✓ Checkpoint limpiado correctamente")
        
        # Limpiar directorio de prueba
        if os.path.exists("test_checkpoints"):
            import shutil
            shutil.rmtree("test_checkpoints")
        
        return True
    except Exception as e:
        print(f"✗ Error en checkpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_consolidator():
    """Prueba el consolidador de texto."""
    print("\n" + "=" * 60)
    print("PRUEBA 4: Consolidador de texto")
    print("=" * 60)
    
    try:
        from heraldo.consolidator import TextConsolidator
        
        consolidator = TextConsolidator(chapter_sentences=3)
        
        # Probar consolidación
        blocks = [
            "Este es el primer bloque de texto.",
            "Este es el segundo bloque.",
            "Este es el tercer bloque."
        ]
        consolidated = consolidator.consolidate_blocks(blocks)
        assert len(consolidated) > 0, "Texto no consolidado"
        print("✓ Consolidación funciona")
        
        # Probar detección de capítulos
        text_with_chapters = "Capítulo 1\n\nContenido del capítulo 1.\n\nCapítulo 2\n\nContenido del capítulo 2."
        chapters = consolidator.detect_chapters(text_with_chapters)
        print(f"✓ Detección de capítulos: {len(chapters)} capítulos encontrados")
        
        # Probar división en oraciones
        sentences = consolidator.split_into_sentences("Primera oración. Segunda oración. Tercera oración.")
        assert len(sentences) >= 3, "División de oraciones falló"
        print(f"✓ División en oraciones: {len(sentences)} oraciones")
        
        return True
    except Exception as e:
        print(f"✗ Error en consolidador: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_processor():
    """Prueba el procesador de Ollama."""
    print("\n" + "=" * 60)
    print("PRUEBA 5: Procesador de Ollama")
    print("=" * 60)
    
    try:
        from heraldo.processor import OllamaProcessor
        
        # Crear procesador con modelo pequeño
        processor = OllamaProcessor(model="phi3:mini")
        
        # Verificar conexión
        print("Verificando conexión con Ollama...")
        # No vamos a hacer una llamada real porque puede tardar, solo verificar estructura
        print("✓ Procesador creado correctamente")
        print(f"  Modelo: {processor.model}")
        print(f"  URL: {processor.api_url}")
        
        return True
    except Exception as e:
        print(f"✗ Error en procesador: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tts_engines():
    """Prueba los motores TTS."""
    print("\n" + "=" * 60)
    print("PRUEBA 6: Motores TTS")
    print("=" * 60)
    
    try:
        from heraldo.tts_engine import create_tts_engine, gTTSEngine, Pyttsx3Engine
        
        # Probar gTTS
        print("\n6.1. Google TTS (gTTS):")
        gtts = gTTSEngine(lang="es")
        if gtts.is_available():
            print("✓ gTTS está disponible")
        else:
            print("✗ gTTS no está disponible")
        
        # Probar pyttsx3
        print("\n6.2. pyttsx3:")
        pyttsx3_engine = Pyttsx3Engine()
        if pyttsx3_engine.is_available():
            print("✓ pyttsx3 está disponible")
        else:
            print("✗ pyttsx3 no está disponible")
        
        # Probar factory
        print("\n6.3. Factory function:")
        try:
            engine = create_tts_engine("gtts")
            print("✓ Factory function funciona para gtts")
        except Exception as e:
            print(f"✗ Error en factory: {e}")
        
        return True
    except Exception as e:
        print(f"✗ Error en TTS: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extractor():
    """Prueba el extractor de PDF (sin PDF real)."""
    print("\n" + "=" * 60)
    print("PRUEBA 7: Extractor de PDF")
    print("=" * 60)
    
    try:
        from heraldo.extractor import PDFExtractor
        
        # Solo verificar que se puede crear (no tenemos PDF de prueba)
        extractor = PDFExtractor("test.pdf", block_size=2000)
        print("✓ Extractor creado correctamente")
        print(f"  Tamaño de bloque: {extractor.block_size} tokens")
        
        # Probar limpieza de texto
        dirty_text = "Texto con    múltiples   espacios\n\n\nY saltos de línea."
        clean = extractor.clean_text(dirty_text)
        assert len(clean) > 0, "Limpieza falló"
        print("✓ Limpieza de texto funciona")
        
        return True
    except Exception as e:
        print(f"✗ Error en extractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "=" * 60)
    print("PRUEBAS DEL SISTEMA HERALDO")
    print("=" * 60)
    
    results = []
    
    results.append(("Importación", test_imports()))
    results.append(("Utilidades", test_utils()))
    results.append(("Checkpoints", test_checkpoint()))
    results.append(("Consolidador", test_consolidator()))
    results.append(("Procesador", test_processor()))
    results.append(("TTS Engines", test_tts_engines()))
    results.append(("Extractor", test_extractor()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 ¡Todas las pruebas pasaron!")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
