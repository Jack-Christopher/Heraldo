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

from dotenv import load_dotenv

from .extractor import PDFExtractor
from .processor import OllamaProcessor, DeepSeekProcessor
from .consolidator import TextConsolidator
from .checkpoint import CheckpointManager
from .tts_engine import create_tts_engine
from .utils import validate_pdf, get_pdf_name, ensure_directory, get_unique_output_dir, count_tokens


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
        chapter_words: int = 500,
        resume: bool = False,
        merge_audio: bool = True,
        tts_lang: str = "es",
        use_ai: bool = False,
        clean_pdf: bool = False,
        overwrite: bool = False,
        piper_max_chunk: int = 2000,
        piper_length_scale: float = 1.0,
        piper_noise_scale: float = 0.667,
        piper_noise_w: float = 0.8,
        piper_sentence_silence: float = 0.3,
        piper_speaker: int = 0,
        ai_provider: str = "ollama",
        max_pages: Optional[int] = None,
        max_tokens: Optional[int] = None,
        force: bool = False,
        deepseek_api_key: Optional[str] = None,
        xtts_speaker_wav: Optional[str] = None,
        xtts_no_cuda: bool = False,
        ai_style: str = "divulgacion",
    ):
        """
        Inicializa el pipeline de Heraldo.

        Args:
            pdf_path: Ruta al archivo PDF
            output_dir: Directorio de salida (default: outputs/{pdf_name})
            model: Modelo de Ollama o DeepSeek a usar
            tts_engine_name: Nombre del motor TTS
            voice: Voz específica (depende del motor)
            block_size: Tamaño de bloque en tokens
            chapter_words: Palabras por bloque (default: 500)
            resume: Si True, intenta reanudar desde checkpoint
            use_ai: Si True, usa IA para procesar el texto. Si False, usa texto directo.
            clean_pdf: Si True, limpia el PDF. Si False, usa texto crudo.
            ai_provider: "ollama" o "deepseek"
            max_pages: Límite de páginas (DeepSeek). Si se supera y no --force, se detiene.
            max_tokens: Límite de tokens (DeepSeek). Si se supera y no --force, se detiene.
            force: Si True, ignorar límites de páginas/tokens con DeepSeek.
            deepseek_api_key: Token de API de DeepSeek (solo si ai_provider == "deepseek").
            ai_style: Estilo de procesamiento: divulgacion, narrativo, filosofia, ensayo, tecnico, poesia
        """
        self.pdf_path = pdf_path
        self.pdf_name = get_pdf_name(pdf_path)
        self.base_output_dir = output_dir or os.path.join("outputs", self.pdf_name)
        self.output_dir = get_unique_output_dir(self.base_output_dir, overwrite=overwrite)
        self.model = model
        self.tts_engine_name = tts_engine_name
        self.voice = voice
        self.block_size = block_size
        self.chapter_words = chapter_words
        self.resume = resume
        self.use_ai = use_ai
        self.clean_pdf = clean_pdf
        self.ai_provider = ai_provider
        self.max_pages = max_pages
        self.max_tokens = max_tokens
        self.force = force
        self.xtts_speaker_wav = xtts_speaker_wav
        self.xtts_no_cuda = xtts_no_cuda
        self.ai_style = ai_style

        # Inicializar componentes
        self.extractor = PDFExtractor(pdf_path, block_size)
        if use_ai:
            if ai_provider == "deepseek":
                if not deepseek_api_key:
                    raise ValueError(
                        "DEEPSEEK_API_KEY no está definido. "
                        "Configúralo en .env o exporta la variable de entorno."
                    )
                estimated_timeout = 600 + (block_size // 1000) * 60
                estimated_timeout = min(estimated_timeout, 1800)
                self.processor = DeepSeekProcessor(
                    api_key=deepseek_api_key,
                    model=model,
                    timeout=estimated_timeout,
                    max_tokens=min(block_size * 2, 4000),
                    ai_style=ai_style,
                )
            else:
                estimated_timeout = 600 + (block_size // 1000) * 60
                estimated_timeout = min(estimated_timeout, 1800)
                self.processor = OllamaProcessor(
                    model=model,
                    timeout=estimated_timeout,
                    num_predict=min(block_size * 2, 4000),
                    num_ctx=min(block_size * 4, 16384),
                    ai_style=ai_style,
                )
        else:
            self.processor = None
        self.consolidator = TextConsolidator(chapter_words)
        self.checkpoint_manager = CheckpointManager(pdf_path)
        
        # Guardar parámetros adicionales
        self.merge_audio = merge_audio
        self.tts_lang = tts_lang
        self.piper_max_chunk = piper_max_chunk
        self.piper_length_scale = piper_length_scale
        self.piper_noise_scale = piper_noise_scale
        self.piper_noise_w = piper_noise_w
        self.piper_sentence_silence = piper_sentence_silence
        self.piper_speaker = piper_speaker

        # Inicializar motor TTS
        tts_kwargs = {}
        if voice:
            tts_kwargs["voice"] = voice
        
        # Agregar parámetros específicos para cada motor
        if tts_engine_name == "piper":
            tts_kwargs["lang"] = tts_lang
            tts_kwargs["max_chunk_length"] = piper_max_chunk
            tts_kwargs["length_scale"] = piper_length_scale
            tts_kwargs["noise_scale"] = piper_noise_scale
            tts_kwargs["noise_w"] = piper_noise_w
            tts_kwargs["sentence_silence"] = piper_sentence_silence
            tts_kwargs["speaker"] = piper_speaker
        elif tts_engine_name == "gtts":
            tts_kwargs["lang"] = tts_lang
        elif tts_engine_name == "xtts":
            tts_kwargs["lang"] = tts_lang
            tts_kwargs["speaker_wav"] = tts_kwargs.get("voice") or self.xtts_speaker_wav
            tts_kwargs["use_cuda"] = not self.xtts_no_cuda

        # Intentar crear el motor TTS solicitado
        try:
            self.tts_engine = create_tts_engine(tts_engine_name, **tts_kwargs)
            
            if tts_engine_name == "piper" and not self.tts_engine.is_available():
                print("Advertencia: Piper TTS no está disponible. Cambiando a gtts...")
                tts_engine_name = "gtts"
                tts_kwargs = {"lang": tts_lang}
                self.tts_engine = create_tts_engine(tts_engine_name, **tts_kwargs)
            elif tts_engine_name == "xtts" and not self.tts_engine.is_available():
                print("Advertencia: XTTS no está disponible. Cambiando a gtts...")
                tts_engine_name = "gtts"
                tts_kwargs = {"lang": tts_lang}
                self.tts_engine = create_tts_engine(tts_engine_name, **tts_kwargs)
        except Exception as e:
            if tts_engine_name in ("piper", "xtts"):
                print(f"Advertencia: Error con {tts_engine_name}: {e}. Cambiando a gtts...")
                tts_engine_name = "gtts"
                tts_kwargs = {"lang": tts_lang}
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
        
        # Informar si se usó un directorio alternativo
        if self.output_dir != self.base_output_dir:
            print(f"Nota: El directorio '{self.base_output_dir}' ya existe.")
            print(f"Usando directorio alternativo: '{self.output_dir}'")
            print("(Usa --overwrite para sobrescribir el directorio existente)")
    
    def run(self):
        """
        Ejecuta el pipeline completo de procesamiento.
        """
        print("=" * 60)
        print("Heraldo - Sistema de Conversión PDF a Audiolibro")
        print("=" * 60)
        print(f"PDF: {self.pdf_path}")
        print(f"Usar IA: {'Sí' if self.use_ai else 'No'}")
        print(f"Limpiar PDF: {'Sí' if self.clean_pdf else 'No'}")
        if self.use_ai:
            print(f"Proveedor IA: {self.ai_provider} (modelo: {self.model})")
            print(f"Estilo IA: {self.ai_style}")
        print(f"Motor TTS: {self.tts_engine_name}")
        print(f"Directorio de salida: {self.output_dir}")
        print("=" * 60)
        
        # Fase 1: Extracción (y opcionalmente limpieza)
        if self.resume and self.checkpoint_manager.should_resume() and self.use_ai:
            print("\n[Fase 1] Reanudando desde checkpoint...")
            resume_data = self.checkpoint_manager.get_resume_data()
            blocks = None  # No necesitamos extraer de nuevo
            processed_blocks = resume_data["processed_blocks"]
            start_block = resume_data["last_block"] + 1
            total_blocks = resume_data["total_blocks"]
        else:
            if self.clean_pdf:
                print("\n[Fase 1] Extrayendo y limpiando texto del PDF...")
            else:
                print("\n[Fase 1] Extrayendo texto del PDF (sin limpieza)...")
            blocks = self.extractor.process(clean=self.clean_pdf)
            processed_blocks = []
            start_block = 0
            total_blocks = len(blocks)
        
        # Guardar texto extraído en archivo .txt
        raw_text_path = os.path.join(self.output_dir, "texto_extraido.txt")
        if blocks is not None and (not self.use_ai or not (self.resume and self.checkpoint_manager.should_resume())):
            # Solo guardar si no estamos reanudando y tenemos bloques
            full_text = "\n\n".join(blocks)
            with open(raw_text_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            print(f"Texto extraído guardado en: {raw_text_path}")
        
        # Fase 2: Procesamiento con IA (solo si está habilitado)
        if self.use_ai:
            print(f"\n[Fase 2] Procesando {total_blocks} bloques con IA...")

            if blocks is None:
                # Si estamos reanudando, necesitamos extraer los bloques de nuevo
                # pero solo procesar los que faltan
                blocks = self.extractor.process(clean=self.clean_pdf)
                if len(blocks) != total_blocks:
                    print("Advertencia: El número de bloques ha cambiado. Reiniciando procesamiento.")
                    processed_blocks = []
                    start_block = 0
                    total_blocks = len(blocks)

            # Límite de seguridad para DeepSeek (páginas/tokens)
            if (
                self.ai_provider == "deepseek"
                and (self.max_pages is not None or self.max_tokens is not None)
                and not self.force
            ):
                import pdfplumber
                with pdfplumber.open(self.pdf_path) as pdf:
                    num_pages = len(pdf.pages)
                total_tokens_blocks = sum(count_tokens(b) for b in blocks)
                over_pages = self.max_pages is not None and num_pages > self.max_pages
                over_tokens = self.max_tokens is not None and total_tokens_blocks > self.max_tokens
                if over_pages or over_tokens:
                    print("Error: Se superó el límite de seguridad para DeepSeek.", file=sys.stderr)
                    if over_pages:
                        print(
                            f"  Páginas: {num_pages} (límite: {self.max_pages}). "
                            "Usa --max-pages o DEEPSEEK_MAX_PAGES para aumentar o --force para ignorar.",
                            file=sys.stderr,
                        )
                    if over_tokens:
                        print(
                            f"  Tokens (aprox.): {total_tokens_blocks} (límite: {self.max_tokens}). "
                            "Usa --max-tokens o DEEPSEEK_MAX_TOKENS para aumentar o --force para ignorar.",
                            file=sys.stderr,
                        )
                    sys.exit(1)

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
        else:
            # Si no se usa IA, usar los bloques directamente
            print("\n[Fase 2] Saltando procesamiento con IA (modo simple)...")
            processed_blocks = blocks
        
        # Fase 3: Consolidación
        print("\n[Fase 3] Consolidando y organizando texto...")
        
        # En modo simple, si no se usa IA, forzar división en capítulos pequeños
        # para evitar pasar textos gigantes a TTS
        if not self.use_ai:
            # Consolidar bloques primero
            consolidated_text = self.consolidator.consolidate_blocks(processed_blocks)
            # Forzar división en capítulos pequeños basados en oraciones (ignorar detección)
            print(f"Dividiendo texto en bloques de {self.chapter_words} palabras (modo simple)...")
            chapters = self.consolidator.split_into_chapters(consolidated_text, detected_chapters=None)
            chapters_detected = False
        else:
            # En modo con IA, usar el proceso normal de consolidación
            chapters, chapters_detected = self.consolidator.process(processed_blocks)
        
        # Guardar texto consolidado
        consolidated_text_path = os.path.join(self.output_dir, "texto_procesado.txt")
        with open(consolidated_text_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(chapters))
        print(f"Texto consolidado guardado en: {consolidated_text_path}")
        
        # Fase 4: Conversión a audio
        # Confiamos en que chapter_words ya dividió el texto en bloques manejables
        # Los motores TTS manejarán el chunking interno si es necesario
        print(f"\n[Fase 4] Generando {len(chapters)} archivos de audio...")
        
        audio_files = []
        for i, chapter in enumerate(tqdm(chapters, desc="Generando audio")):
            output_filename = f"bloque_{i+1:03d}.wav"
            output_path = os.path.join(self.output_dir, output_filename)
            
            try:
                # El motor TTS manejará el chunking internamente si es necesario
                success = self.tts_engine.synthesize(chapter, output_path)
                
                if success and os.path.exists(output_path):
                    audio_files.append(output_path)
                else:
                    print(f"\nAdvertencia: No se pudo generar audio para el bloque {i+1}")
                    print(f"  Ruta intentada: {output_path}")
                    print(f"  Longitud del texto: {len(chapter)} caracteres (~{len(chapter.split())} palabras)")
                    print(f"  Motor TTS: {self.tts_engine_name}")
            except Exception as e:
                print(f"\nError al generar audio para el bloque {i+1}: {e}")
                import traceback
                traceback.print_exc()
        
        # Mergear audios si está habilitado y hay múltiples archivos
        if self.merge_audio and len(audio_files) > 1:
            print(f"\nMergeando {len(audio_files)} archivos de audio...")
            merged_path = os.path.join(self.output_dir, f"{self.pdf_name}.wav")
            if self._merge_audio_files(audio_files, merged_path):
                print(f"✓ Audio completo guardado en: {merged_path}")
            else:
                print("⚠ No se pudo mergear los archivos de audio")
        elif self.merge_audio and len(audio_files) == 1:
            # Si solo hay un archivo, renombrarlo al nombre del PDF
            if audio_files:
                import shutil
                merged_path = os.path.join(self.output_dir, f"{self.pdf_name}.wav")
                shutil.copy2(audio_files[0], merged_path)
                print(f"✓ Audio guardado en: {merged_path}")
        
        # Limpiar checkpoint al completar (solo si se usó IA)
        if self.use_ai:
            self.checkpoint_manager.clear_checkpoint()
        
        print("\n" + "=" * 60)
        print("¡Procesamiento completado!")
        print(f"Archivos guardados en: {self.output_dir}")
        print(f"  - Texto extraído: {raw_text_path}")
        if self.use_ai:
            print(f"  - Texto procesado: {consolidated_text_path}")
        if self.merge_audio and audio_files:
            print(f"  - Audio completo: {os.path.join(self.output_dir, f'{self.pdf_name}.wav')}")
        print("=" * 60)
    
    def _merge_audio_files(self, audio_files: List[str], output_path: str) -> bool:
        """
        Combina múltiples archivos de audio WAV en uno solo.
        Usa pydub para normalizar parámetros distintos (sample rate, canales).
        """
        return _merge_wav_files(audio_files, output_path)


def _merge_wav_files(audio_files: List[str], output_path: str) -> bool:
    """
    Combina múltiples WAV en uno. Usa pydub para normalizar parámetros distintos.
    """
    if not audio_files:
        return False
    try:
        from pydub import AudioSegment
        target = AudioSegment.from_wav(audio_files[0])
        for f in audio_files[1:]:
            if not os.path.exists(f):
                continue
            seg = AudioSegment.from_wav(f)
            if seg.frame_rate != target.frame_rate:
                seg = seg.set_frame_rate(target.frame_rate)
            if seg.channels != target.channels:
                seg = seg.set_channels(target.channels)
            if seg.sample_width != target.sample_width:
                seg = seg.set_sample_width(target.sample_width)
            target += seg
        target.export(output_path, format="wav")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except ImportError:
        import wave
        try:
            with wave.open(audio_files[0], "rb") as first:
                params = first.getparams()
                with wave.open(output_path, "wb") as outfile:
                    outfile.setparams(params)
                    for f in audio_files:
                        if os.path.exists(f):
                            with wave.open(f, "rb") as infile:
                                if infile.getparams() == params:
                                    outfile.writeframes(infile.readframes(infile.getnframes()))
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception:
            return False
    except Exception:
        return False


def _run_solo_audio(args) -> None:
    """
    Ejecuta solo la Fase 4 (generación de audio) desde un directorio que ya tiene
    texto_procesado.txt (por una ejecución anterior). No requiere --pdf.
    """
    output_dir = os.path.abspath(args.solo_audio)
    text_path = os.path.join(output_dir, "texto_procesado.txt")
    if not os.path.exists(text_path):
        print(f"Error: No existe {text_path}. Ejecuta primero el pipeline completo (con --pdf) para generar el texto.", file=sys.stderr)
        sys.exit(1)

    with open(text_path, "r", encoding="utf-8") as f:
        content = f.read()
    chapters = [c.strip() for c in content.split("\n\n") if c.strip()]
    if not chapters:
        print("Error: texto_procesado.txt está vacío o no tiene bloques (separados por doble salto de línea).", file=sys.stderr)
        sys.exit(1)

    tts_kwargs = {}
    if args.voice:
        tts_kwargs["voice"] = args.voice
    if args.tts_engine == "piper":
        tts_kwargs["lang"] = args.tts_lang
        tts_kwargs["max_chunk_length"] = args.piper_max_chunk
        tts_kwargs["length_scale"] = args.piper_length_scale
        tts_kwargs["noise_scale"] = args.piper_noise_scale
        tts_kwargs["noise_w"] = args.piper_noise_w
        tts_kwargs["sentence_silence"] = args.piper_sentence_silence
        tts_kwargs["speaker"] = args.piper_speaker
    elif args.tts_engine == "xtts":
        tts_kwargs["lang"] = args.tts_lang
        tts_kwargs["speaker_wav"] = args.voice or args.xtts_speaker_wav
        tts_kwargs["use_cuda"] = not args.no_xtts_cuda
    elif args.tts_engine == "gtts":
        tts_kwargs["lang"] = args.tts_lang

    try:
        tts_engine = create_tts_engine(args.tts_engine, **tts_kwargs)
    except Exception as e:
        print(f"Error al crear motor TTS: {e}", file=sys.stderr)
        sys.exit(1)
    if not tts_engine.is_available():
        print(f"Error: El motor TTS '{args.tts_engine}' no está disponible.", file=sys.stderr)
        sys.exit(1)

    merge_audio = not args.no_merge_audio
    print("=" * 60)
    print("Heraldo - Solo Fase 4 (audio desde texto existente)")
    print("=" * 60)
    print(f"Directorio: {output_dir}")
    print(f"Bloques a sintetizar: {len(chapters)}")
    print(f"Motor TTS: {args.tts_engine}")
    print("=" * 60)
    print(f"\n[Fase 4] Generando {len(chapters)} archivos de audio...")

    audio_files = []
    for i, chapter in enumerate(tqdm(chapters, desc="Generando audio")):
        output_path = os.path.join(output_dir, f"bloque_{i+1:03d}.wav")
        try:
            success = tts_engine.synthesize(chapter, output_path)
            if success and os.path.exists(output_path):
                audio_files.append(output_path)
            else:
                print(f"\nAdvertencia: No se pudo generar audio para el bloque {i+1}")
        except Exception as e:
            print(f"\nError al generar audio para el bloque {i+1}: {e}")
            import traceback
            traceback.print_exc()

    pdf_name = os.path.basename(os.path.normpath(output_dir))
    if merge_audio and len(audio_files) > 1:
        print(f"\nMergeando {len(audio_files)} archivos de audio...")
        merged_path = os.path.join(output_dir, f"{pdf_name}.wav")
        if _merge_wav_files(audio_files, merged_path):
            print(f"✓ Audio completo guardado en: {merged_path}")
        else:
            print("⚠ No se pudo mergear. Instala pydub: pip install pydub")
    elif merge_audio and len(audio_files) == 1:
        import shutil
        merged_path = os.path.join(output_dir, f"{pdf_name}.wav")
        shutil.copy2(audio_files[0], merged_path)
        print(f"✓ Audio guardado en: {merged_path}")

    print("\n" + "=" * 60)
    print("¡Generación de audio completada!")
    print(f"Archivos en: {output_dir}")
    if merge_audio and audio_files:
        print(f"  - Audio completo: {os.path.join(output_dir, f'{pdf_name}.wav')}")
    print("=" * 60)


def main():
    """
    Función principal con interfaz de línea de comandos.
    """
    parser = argparse.ArgumentParser(
        description="Heraldo - Convierte PDFs en audiolibros (modo simple por defecto)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Modo simple (por defecto): solo extrae texto y convierte a audio
  python -m heraldo.main --pdf documento.pdf
  
  # Con limpieza de PDF (sin IA)
  python -m heraldo.main --pdf documento.pdf --clean-pdf
  
  # Con procesamiento de IA (enriquecido)
  python -m heraldo.main --pdf documento.pdf --use-ai
  
  # Con limpieza y IA
  python -m heraldo.main --pdf documento.pdf --use-ai --clean-pdf
  
  # Con opciones personalizadas
  python -m heraldo.main --pdf documento.pdf --use-ai --model qwen2.5:14b --tts-engine gtts

  # Libro de filosofía: la IA explicará conceptos y dará contexto
  python -m heraldo.main --pdf filosofia.pdf --use-ai --ai-style filosofia

  # Novela: enfocarse en la experiencia narrativa
  python -m heraldo.main --pdf novela.pdf --use-ai --ai-style narrativo
  
  # Reanudar procesamiento (solo con --use-ai)
  python -m heraldo.main --pdf documento.pdf --use-ai --resume

  # Solo generar audio desde texto ya procesado (Fase 4)
  python -m heraldo.main --solo-audio outputs/mi_libro
        """
    )
    
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Ruta al archivo PDF a procesar (requerido salvo con --solo-audio)"
    )

    parser.add_argument(
        "--solo-audio",
        type=str,
        default=None,
        metavar="DIR",
        help="Solo Fase 4: generar audio desde texto ya procesado. DIR debe contener texto_procesado.txt. Omite --pdf y fases 1-3."
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
        help="Modelo de IA: con Ollama default phi3:mini; con DeepSeek se usa deepseek-chat si no indicas otro"
    )
    
    parser.add_argument(
        "--tts-engine",
        type=str,
        default="piper",
        choices=["piper", "gtts", "xtts"],
        help="Motor TTS a usar (default: piper)"
    )
    
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help=(
            "Voz específica para el motor TTS. "
            "Piper: nombre del modelo (ej: es_ES-davefx-medium) o ruta al .onnx. "
            "XTTS: ruta a WAV de referencia o nombre built-in (ej: Ana Florence). "
            "Descarga voces Piper desde: https://huggingface.co/rhasspy/piper-voices"
        )
    )
    
    parser.add_argument(
        "--block-size",
        type=int,
        default=2000,
        help="Tamaño de bloque en tokens (default: 2000)"
    )
    
    parser.add_argument(
        "--chapter-words",
        type=int,
        default=500,
        help="Palabras por bloque (default: 500). Se aplica siempre, incluso si hay capítulos detectados"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanudar procesamiento desde el último checkpoint"
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
    
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Usar IA para procesar y enriquecer el texto (default: False, modo simple)"
    )
    
    parser.add_argument(
        "--clean-pdf",
        action="store_true",
        help="Limpiar el PDF eliminando encabezados, pies de página, etc. (default: False, texto crudo)"
    )
    
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribir el directorio de salida si ya existe (default: False, se crea un directorio único)"
    )
    
    parser.add_argument(
        "--piper-max-chunk",
        type=int,
        default=2000,
        help="Longitud máxima de texto por chunk para Piper TTS en caracteres (default: 2000)"
    )

    parser.add_argument(
        "--piper-length-scale",
        type=float,
        default=1.0,
        metavar="NUM",
        help="Duración de fonemas; <1 más rápido, >1 más lento (default: 1.0)"
    )

    parser.add_argument(
        "--piper-noise-scale",
        type=float,
        default=0.667,
        metavar="NUM",
        help="Ruido del generador Piper (default: 0.667)"
    )

    parser.add_argument(
        "--piper-noise-w",
        type=float,
        default=0.8,
        metavar="NUM",
        help="Ruido de ancho de fonemas Piper (default: 0.8)"
    )

    parser.add_argument(
        "--piper-sentence-silence",
        type=float,
        default=0.3,
        metavar="SEC",
        help="Segundos de silencio entre oraciones (default: 0.3)"
    )

    parser.add_argument(
        "--piper-speaker",
        type=int,
        default=0,
        metavar="ID",
        help="ID de hablante en modelos multi-speaker (default: 0)"
    )

    parser.add_argument(
        "--xtts-speaker-wav",
        type=str,
        default=None,
        help="Ruta a WAV de referencia para XTTS (clonación de voz). Alternativa: usa --voice con la ruta."
    )

    parser.add_argument(
        "--no-xtts-cuda",
        action="store_true",
        default=False,
        help="Desactivar GPU para XTTS (usar CPU). Por defecto se usa GPU si está disponible."
    )

    parser.add_argument(
        "--ai-style",
        type=str,
        default="divulgacion",
        choices=["divulgacion", "narrativo", "filosofia", "ensayo", "tecnico", "poesia"],
        help=(
            "Estilo de procesamiento IA: divulgacion (default), narrativo, filosofia, ensayo, tecnico, poesia. "
            "Define cómo la IA adapta el contenido (narrativo: experiencia y fluidez; filosofia: explicar conceptos; etc.)"
        ),
    )

    parser.add_argument(
        "--ai-provider",
        type=str,
        default="ollama",
        choices=["ollama", "deepseek"],
        help="Proveedor de IA: ollama (local) o deepseek (API). Default: ollama"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Límite de páginas del PDF al usar DeepSeek. Si se supera, el pipeline se detiene (usa --force para ignorar). También se puede definir DEEPSEEK_MAX_PAGES en .env"
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Límite de tokens (aprox.) al usar DeepSeek. Si se supera, el pipeline se detiene (usa --force para ignorar). También se puede definir DEEPSEEK_MAX_TOKENS en .env"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignorar límites de páginas/tokens cuando se usa DeepSeek"
    )

    args = parser.parse_args()

    load_dotenv()

    # Modo solo-audio: solo Fase 4 desde texto ya procesado
    if args.solo_audio:
        _run_solo_audio(args)
        return

    if not args.pdf:
        print("Error: Indica --pdf con la ruta al PDF (o usa --solo-audio DIR para solo generar audio).", file=sys.stderr)
        sys.exit(1)

    # Validar PDF
    try:
        validate_pdf(args.pdf)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Validar que resume solo se use con --use-ai
    if args.resume and not args.use_ai:
        print("Advertencia: --resume solo funciona con --use-ai. Ignorando --resume.")
        args.resume = False

    # DeepSeek: exigir API key cuando el proveedor es deepseek y se usa IA
    if args.use_ai and args.ai_provider == "deepseek":
        if not os.getenv("DEEPSEEK_API_KEY"):
            print(
                "Error: Con --ai-provider deepseek se requiere DEEPSEEK_API_KEY. "
                "Configúralo en .env o exporta la variable de entorno.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Resolver límites desde CLI o .env (solo aplican a DeepSeek)
    max_pages = args.max_pages
    if max_pages is None and os.getenv("DEEPSEEK_MAX_PAGES"):
        try:
            max_pages = int(os.getenv("DEEPSEEK_MAX_PAGES", ""))
        except ValueError:
            pass
    max_tokens = args.max_tokens
    if max_tokens is None and os.getenv("DEEPSEEK_MAX_TOKENS"):
        try:
            max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", ""))
        except ValueError:
            pass

    # Con DeepSeek usar modelo válido de la API (phi3:mini es de Ollama)
    model = args.model
    if args.ai_provider == "deepseek" and args.model == "phi3:mini":
        model = "deepseek-chat"

    # Crear y ejecutar pipeline
    try:
        pipeline = HeraldoPipeline(
            pdf_path=args.pdf,
            output_dir=args.output,
            model=model,
            tts_engine_name=args.tts_engine,
            voice=args.voice,
            block_size=args.block_size,
            chapter_words=args.chapter_words,
            resume=args.resume,
            merge_audio=not args.no_merge_audio,
            tts_lang=args.tts_lang,
            use_ai=args.use_ai,
            clean_pdf=args.clean_pdf,
            overwrite=args.overwrite,
            piper_max_chunk=args.piper_max_chunk,
            piper_length_scale=args.piper_length_scale,
            piper_noise_scale=args.piper_noise_scale,
            piper_noise_w=args.piper_noise_w,
            piper_sentence_silence=args.piper_sentence_silence,
            piper_speaker=args.piper_speaker,
            ai_provider=args.ai_provider,
            max_pages=max_pages,
            max_tokens=max_tokens,
            force=args.force,
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") if args.ai_provider == "deepseek" else None,
            xtts_speaker_wav=args.xtts_speaker_wav,
            xtts_no_cuda=args.no_xtts_cuda,
            ai_style=args.ai_style,
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
