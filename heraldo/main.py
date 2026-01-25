"""
Punto de entrada principal del sistema Heraldo.
Orquesta todas las fases del procesamiento de PDF a audiolibro.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List
from tqdm import tqdm

from .extractor import PDFExtractor
from .processor import OllamaProcessor
from .consolidator import TextConsolidator
from .checkpoint import CheckpointManager
from .tts_engine import create_tts_engine
from .utils import validate_pdf, get_pdf_name, ensure_directory


class HeraldoPipeline:
    """
    Pipeline principal que orquesta todas las fases del procesamiento.
    """
    
    def __init__(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        model: str = "phi3:mini",
        tts_engine_name: str = "piper",
        voice: Optional[str] = None,
        block_size: int = 2000,
        chapter_sentences: int = 50,
        resume: bool = False,
        tts_sentences_per_chunk: int = 10,
        merge_audio: bool = True,
        tts_lang: str = "es"
    ):
        """
        Inicializa el pipeline de Heraldo.
        
        Args:
            pdf_path: Ruta al archivo PDF
            output_dir: Directorio de salida (default: outputs/{pdf_name})
            model: Modelo de Ollama a usar
            tts_engine_name: Nombre del motor TTS
            voice: Voz específica (depende del motor)
            block_size: Tamaño de bloque en tokens
            chapter_sentences: Oraciones por capítulo si no se detectan
            resume: Si True, intenta reanudar desde checkpoint
        """
        self.pdf_path = pdf_path
        self.pdf_name = get_pdf_name(pdf_path)
        self.output_dir = output_dir or os.path.join("outputs", self.pdf_name)
        self.model = model
        self.tts_engine_name = tts_engine_name
        self.voice = voice
        self.block_size = block_size
        self.chapter_sentences = chapter_sentences
        self.resume = resume
        
        # Inicializar componentes
        self.extractor = PDFExtractor(pdf_path, block_size)
        self.processor = OllamaProcessor(model)
        self.consolidator = TextConsolidator(chapter_sentences)
        self.checkpoint_manager = CheckpointManager(pdf_path)
        
        # Guardar parámetros adicionales
        self.tts_sentences_per_chunk = tts_sentences_per_chunk
        self.merge_audio = merge_audio
        self.tts_lang = tts_lang
        
        # Inicializar motor TTS
        tts_kwargs = {}
        if voice:
            tts_kwargs["voice"] = voice
        
        # Agregar parámetros específicos para cada motor
        if tts_engine_name == "pyttsx3":
            tts_kwargs["sentences_per_chunk"] = tts_sentences_per_chunk
            tts_kwargs["lang"] = tts_lang
        elif tts_engine_name == "piper":
            # Agregar idioma para seleccionar voz por defecto si no se especifica
            tts_kwargs["lang"] = tts_lang
        
        # Intentar crear el motor TTS solicitado
        try:
            self.tts_engine = create_tts_engine(tts_engine_name, **tts_kwargs)
            
            # Si piper no está disponible o no tiene voz, hacer fallback a pyttsx3
            if tts_engine_name == "piper" and not self.tts_engine.is_available():
                print("Advertencia: Piper TTS no está disponible. Cambiando a pyttsx3...")
                tts_engine_name = "pyttsx3"
                tts_kwargs = {"sentences_per_chunk": tts_sentences_per_chunk, "lang": tts_lang}
                self.tts_engine = create_tts_engine(tts_engine_name, **tts_kwargs)
        except Exception as e:
            # Si hay error con piper (ej: modelo no encontrado), hacer fallback
            if tts_engine_name == "piper":
                print(f"Advertencia: Error con Piper TTS: {e}. Cambiando a pyttsx3...")
                tts_engine_name = "pyttsx3"
                tts_kwargs = {"sentences_per_chunk": tts_sentences_per_chunk, "lang": tts_lang}
                self.tts_engine = create_tts_engine(tts_engine_name, **tts_kwargs)
            else:
                raise
        
        # Verificar que el motor TTS está disponible
        if not self.tts_engine.is_available():
            raise RuntimeError(
                f"El motor TTS '{tts_engine_name}' no está disponible. "
                f"Verifica la instalación y configuración."
            )
        
        # Asegurar que el directorio de salida existe
        ensure_directory(self.output_dir)
    
    def run(self):
        """
        Ejecuta el pipeline completo de procesamiento.
        """
        print("=" * 60)
        print("Heraldo - Sistema de Conversión PDF a Audiolibro")
        print("=" * 60)
        print(f"PDF: {self.pdf_path}")
        print(f"Modelo IA: {self.model}")
        print(f"Motor TTS: {self.tts_engine_name}")
        print(f"Directorio de salida: {self.output_dir}")
        print("=" * 60)
        
        # Fase 1: Extracción y limpieza
        if self.resume and self.checkpoint_manager.should_resume():
            print("\n[Fase 1] Reanudando desde checkpoint...")
            resume_data = self.checkpoint_manager.get_resume_data()
            blocks = None  # No necesitamos extraer de nuevo
            processed_blocks = resume_data["processed_blocks"]
            start_block = resume_data["last_block"] + 1
            total_blocks = resume_data["total_blocks"]
        else:
            print("\n[Fase 1] Extrayendo y limpiando texto del PDF...")
            blocks = self.extractor.process()
            processed_blocks = []
            start_block = 0
            total_blocks = len(blocks)
        
        # Fase 2: Procesamiento con IA
        print(f"\n[Fase 2] Procesando {total_blocks} bloques con IA...")
        
        if blocks is None:
            # Si estamos reanudando, necesitamos extraer los bloques de nuevo
            # pero solo procesar los que faltan
            blocks = self.extractor.process()
            if len(blocks) != total_blocks:
                print("Advertencia: El número de bloques ha cambiado. Reiniciando procesamiento.")
                processed_blocks = []
                start_block = 0
                total_blocks = len(blocks)
        
        # Procesar bloques con barra de progreso
        failed_blocks = []
        
        for i in tqdm(range(start_block, total_blocks), desc="Procesando bloques"):
            block = blocks[i]
            
            processed = self.processor.process_block(block)
            
            if processed is None:
                print(f"\nError: No se pudo procesar el bloque {i + 1} después de todos los reintentos")
                failed_blocks.append(i)
                # Guardar el bloque original como fallback
                processed_blocks.append(block)
            else:
                processed_blocks.append(processed)
            
            # Guardar checkpoint después de cada bloque exitoso
            self.checkpoint_manager.save_checkpoint(
                last_block=i,
                processed_blocks=processed_blocks,
                total_blocks=total_blocks
            )
        
        if failed_blocks:
            print(f"\nAdvertencia: {len(failed_blocks)} bloques fallaron y se usó el texto original")
        
        # Fase 3: Consolidación
        print("\n[Fase 3] Consolidando y organizando texto...")
        chapters, chapters_detected = self.consolidator.process(processed_blocks)
        
        # Guardar texto consolidado
        consolidated_text_path = os.path.join(self.output_dir, "texto_procesado.txt")
        with open(consolidated_text_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(chapters))
        print(f"Texto consolidado guardado en: {consolidated_text_path}")
        
        # Fase 4: Conversión a audio
        print(f"\n[Fase 4] Generando {len(chapters)} archivos de audio...")
        
        audio_files = []
        for i, chapter in enumerate(tqdm(chapters, desc="Generando audio")):
            output_filename = f"bloque_{i+1:03d}.wav"
            output_path = os.path.join(self.output_dir, output_filename)
            
            try:
                success = self.tts_engine.synthesize(chapter, output_path)
                
                if success and os.path.exists(output_path):
                    audio_files.append(output_path)
                else:
                    print(f"\nAdvertencia: No se pudo generar audio para el bloque {i+1}")
                    print(f"  Ruta intentada: {output_path}")
                    print(f"  Longitud del texto: {len(chapter)} caracteres")
                    print(f"  Motor TTS: {self.tts_engine_name}")
            except Exception as e:
                print(f"\nError al generar audio para el bloque {i+1}: {e}")
                import traceback
                traceback.print_exc()
        
        # Mergear audios si está habilitado y hay múltiples archivos
        if self.merge_audio and len(audio_files) > 1:
            print(f"\nMergeando {len(audio_files)} archivos de audio...")
            merged_path = os.path.join(self.output_dir, "audio_completo.wav")
            if self._merge_audio_files(audio_files, merged_path):
                print(f"✓ Audio completo guardado en: {merged_path}")
            else:
                print("⚠ No se pudo mergear los archivos de audio")
        elif self.merge_audio and len(audio_files) == 1:
            # Si solo hay un archivo, renombrarlo a audio_completo.wav
            if audio_files:
                import shutil
                merged_path = os.path.join(self.output_dir, "audio_completo.wav")
                shutil.copy2(audio_files[0], merged_path)
                print(f"✓ Audio guardado en: {merged_path}")
        
        # Limpiar checkpoint al completar
        self.checkpoint_manager.clear_checkpoint()
        
        print("\n" + "=" * 60)
        print("¡Procesamiento completado!")
        print(f"Archivos guardados en: {self.output_dir}")
        if self.merge_audio and audio_files:
            print(f"Audio completo: {os.path.join(self.output_dir, 'audio_completo.wav')}")
        print("=" * 60)
    
    def _merge_audio_files(self, audio_files: List[str], output_path: str) -> bool:
        """
        Combina múltiples archivos de audio WAV en uno solo.
        
        Args:
            audio_files: Lista de rutas a archivos WAV
            output_path: Ruta donde guardar el archivo combinado
        
        Returns:
            True si la combinación fue exitosa, False en caso contrario
        """
        try:
            import wave
            
            if not audio_files:
                return False
            
            # Leer el primer archivo para obtener parámetros
            with wave.open(audio_files[0], 'rb') as first:
                params = first.getparams()
                
                # Crear archivo de salida
                with wave.open(output_path, 'wb') as outfile:
                    outfile.setparams(params)
                    
                    # Escribir todos los archivos
                    for audio_file in audio_files:
                        if os.path.exists(audio_file):
                            with wave.open(audio_file, 'rb') as infile:
                                # Verificar que los parámetros coincidan
                                if infile.getparams() == params:
                                    outfile.writeframes(infile.readframes(infile.getnframes()))
                                else:
                                    print(f"Advertencia: Parámetros de audio diferentes en {audio_file}, saltando...")
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        
        except Exception as e:
            print(f"Error al mergear archivos de audio: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """
    Función principal con interfaz de línea de comandos.
    """
    parser = argparse.ArgumentParser(
        description="Heraldo - Convierte PDFs extensos en audiolibros educativos enriquecidos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Uso básico
  python -m heraldo.main --pdf documento.pdf
  
  # Con opciones personalizadas
  python -m heraldo.main --pdf documento.pdf --model qwen2.5:14b --tts-engine gtts
  
  # Reanudar procesamiento
  python -m heraldo.main --pdf documento.pdf --resume
        """
    )
    
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="Ruta al archivo PDF a procesar"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directorio de salida (default: outputs/{nombre_pdf})"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="phi3:mini",
        help="Modelo de Ollama a usar (default: phi3:mini)"
    )
    
    parser.add_argument(
        "--tts-engine",
        type=str,
        default="piper",
        choices=["piper", "gtts", "pyttsx3"],
        help="Motor TTS a usar (default: piper)"
    )
    
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="Voz específica (depende del motor TTS)"
    )
    
    parser.add_argument(
        "--block-size",
        type=int,
        default=2000,
        help="Tamaño de bloque en tokens (default: 2000)"
    )
    
    parser.add_argument(
        "--chapter-sentences",
        type=int,
        default=50,
        help="Oraciones por capítulo si no se detectan (default: 50)"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanudar procesamiento desde el último checkpoint"
    )
    
    parser.add_argument(
        "--tts-sentences-per-chunk",
        type=int,
        default=10,
        help="Número de oraciones por chunk para TTS (default: 10, solo para pyttsx3)"
    )
    
    parser.add_argument(
        "--no-merge-audio",
        action="store_true",
        help="No mergear los archivos de audio al final (por defecto se mergean)"
    )
    
    parser.add_argument(
        "--tts-lang",
        type=str,
        default="es",
        help="Idioma para TTS (default: es para español). Opciones: es, en, fr, de, it, pt"
    )
    
    args = parser.parse_args()
    
    # Validar PDF
    try:
        validate_pdf(args.pdf)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Crear y ejecutar pipeline
    try:
        pipeline = HeraldoPipeline(
            pdf_path=args.pdf,
            output_dir=args.output,
            model=args.model,
            tts_engine_name=args.tts_engine,
            voice=args.voice,
            block_size=args.block_size,
            chapter_sentences=args.chapter_sentences,
            resume=args.resume,
            tts_sentences_per_chunk=args.tts_sentences_per_chunk,
            merge_audio=not args.no_merge_audio,
            tts_lang=args.tts_lang
        )
        pipeline.run()
    except KeyboardInterrupt:
        print("\n\nProcesamiento interrumpido por el usuario.")
        print("Puedes reanudar con la opción --resume")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
