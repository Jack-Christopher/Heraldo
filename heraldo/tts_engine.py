"""
Módulo para conversión de texto a voz (TTS) usando múltiples motores.
Fase 4 del sistema Heraldo.
"""

import os
import subprocess
from abc import ABC, abstractmethod
from typing import Optional
from gtts import gTTS


class TTSEngine(ABC):
    """
    Clase base abstracta para motores TTS.
    """
    
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Sintetiza texto a audio y guarda en el archivo especificado.
        
        Args:
            text: Texto a sintetizar
            output_path: Ruta donde guardar el archivo de audio
        
        Returns:
            True si la síntesis fue exitosa, False en caso contrario
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si el motor TTS está disponible y configurado correctamente.
        
        Returns:
            True si está disponible, False en caso contrario
        """
        pass


class PiperTTS(TTSEngine):
    """
    Motor TTS usando Piper (ejecutable local ultra rápido).
    """
    
    def __init__(
        self,
        piper_path: Optional[str] = None,
        voice: Optional[str] = None,
        lang: str = "es",
        max_chunk_length: int = 2000,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
        sentence_silence: float = 0.3,
        speaker: int = 0,
    ):
        """
        Inicializa el motor Piper TTS.

        Args:
            piper_path: Ruta al ejecutable de Piper (o None para usar PATH)
            voice: Nombre del modelo de voz (ej: es_ES-davefx-medium)
            lang: Código de idioma para seleccionar voz por defecto (default: "es")
            max_chunk_length: Longitud máxima de texto por chunk en caracteres (default: 2000)
            length_scale: Duración de fonemas; <1 más rápido, >1 más lento (default: 1.0)
            noise_scale: Ruido del generador; más variabilidad de voz (default: 0.667)
            noise_w: Ruido de ancho de fonemas (default: 0.8)
            sentence_silence: Segundos de silencio entre oraciones (default: 0.3 para audiolibros)
            speaker: ID de hablante en modelos multi-speaker (default: 0)
        """
        def _float_from_env(name: str, default: float) -> float:
            val = os.environ.get(name)
            if val is None:
                return default
            try:
                return float(val)
            except ValueError:
                return default

        self.piper_path = piper_path or os.environ.get("PIPER_PATH", "piper-bin")
        self.voice = voice or os.environ.get("PIPER_VOICE")
        self.max_chunk_length = max_chunk_length
        self.lang = lang
        self.length_scale = _float_from_env("PIPER_LENGTH_SCALE", length_scale)
        self.noise_scale = _float_from_env("PIPER_NOISE_SCALE", noise_scale)
        self.noise_w = _float_from_env("PIPER_NOISE_W", noise_w)
        self.sentence_silence = _float_from_env("PIPER_SENTENCE_SILENCE", sentence_silence)
        env_speaker = os.environ.get("PIPER_SPEAKER")
        if env_speaker is not None:
            try:
                self.speaker = int(env_speaker)
            except ValueError:
                self.speaker = speaker
        else:
            self.speaker = speaker

        # Voces alternativas por idioma (para usar si la principal no está instalada)
        self._lang_voices_alt = {
            'es': ['es_ES-davefx-medium', 'es_ES-shared-medium', 'es_ES-carlfm-medium', 'es_AR-tango-medium', 'es_CO-carlfm-medium', 'es_CL-catalina-medium'],
            'en': ['en_US-lessac-medium', 'en_GB-alba-medium'],
            'fr': ['fr_FR-upmc-medium'],
            'de': ['de_DE-thorsten-medium'],
            'it': ['it_IT-riccardo-medium'],
            'pt': ['pt_BR-faber-medium'],
        }

        # Si voice no está especificado, usar uno por defecto basado en el idioma
        if not self.voice:
            lang_voices = {
                'es': 'es_ES-davefx-medium',
                'en': 'en_US-lessac-medium',
                'fr': 'fr_FR-upmc-medium',
                'de': 'de_DE-thorsten-medium',
                'it': 'it_IT-riccardo-medium',
                'pt': 'pt_BR-faber-medium',
            }
            self.voice = lang_voices.get(lang, lang_voices['es'])
    
    def is_available(self) -> bool:
        """Verifica si Piper está disponible."""
        try:
            result = subprocess.run(
                [self.piper_path, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Sintetiza texto usando Piper TTS.
        Divide el texto en chunks si es muy largo.
        
        Args:
            text: Texto a sintetizar
            output_path: Ruta donde guardar el archivo WAV
        """
        if not self.is_available():
            raise RuntimeError(
                f"Piper TTS no está disponible. "
                f"Verifica que '{self.piper_path}' esté instalado y en el PATH, "
                f"o configura PIPER_PATH."
            )
        
        if not self.voice:
            raise ValueError(
                "No se especificó un modelo de voz para Piper. "
                "Usa --voice o configura PIPER_VOICE."
            )
        
        # Resolver ruta al modelo: probar voz principal y luego alternativas del idioma
        def resolve_voice_path(voice_name: str) -> Optional[str]:
            if os.path.exists(voice_name):
                return voice_name
            if not voice_name.endswith('.onnx') and os.path.exists(f"{voice_name}.onnx"):
                return f"{voice_name}.onnx"
            for path in [
                os.path.join(os.path.expanduser("~"), ".local", "share", "piper", "voices", voice_name, f"{voice_name}.onnx"),
                os.path.join(".", "models", f"{voice_name}.onnx"),
                os.path.join(".", f"{voice_name}.onnx"),
            ]:
                if os.path.exists(path):
                    return path
            return None

        model_path = resolve_voice_path(self.voice)
        if not model_path:
            # Probar voces alternativas del mismo idioma
            for alt_voice in self._lang_voices_alt.get(self.lang, [self.voice]):
                if alt_voice == self.voice:
                    continue
                model_path = resolve_voice_path(alt_voice)
                if model_path:
                    if not getattr(self, "_voice_fallback_reported", False):
                        print(f"  Nota: Usando voz '{alt_voice}' (no se encontró '{self.voice}').")
                        self._voice_fallback_reported = True
                    break
        if not model_path:
            tried = [self.voice] + [v for v in self._lang_voices_alt.get(self.lang, []) if v != self.voice]
            raise FileNotFoundError(
                f"Ningún modelo de voz de Piper encontrado (probados: {', '.join(tried)}). "
                "Descarga un .onnx desde https://huggingface.co/rhasspy/piper-voices/tree/main/es "
                "y colócalo en ./models/ o pasa --voice con la ruta al archivo."
            )

        # Dividir texto en chunks si es muy largo
        if len(text) > self.max_chunk_length:
            # Dividir por oraciones usando nltk o regex
            import re
            try:
                import nltk
                try:
                    sentences = nltk.sent_tokenize(text)
                except (LookupError, Exception):
                    # Fallback: división simple por puntuación
                    sentences = re.split(r'[.!?]+\s+', text)
                    sentences = [s.strip() for s in sentences if s.strip()]
            except ImportError:
                # Si nltk no está disponible, usar regex
                sentences = re.split(r'[.!?]+\s+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
            
            # Crear chunks de aproximadamente max_chunk_length caracteres
            chunks = []
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                # Si agregar esta oración excede el límite y ya hay contenido, guardar chunk
                if current_length + sentence_length > self.max_chunk_length and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [sentence]
                    current_length = sentence_length
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length + 1  # +1 por el espacio
            
            # Agregar el último chunk
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Si hay múltiples chunks, procesar cada uno y combinar
            if len(chunks) > 1:
                import wave
                temp_files = []
                
                for i, chunk in enumerate(chunks):
                    temp_file = output_path.replace('.wav', f'_temp_{i}.wav')
                    temp_dir = os.path.dirname(temp_file)
                    if temp_dir and not os.path.exists(temp_dir):
                        os.makedirs(temp_dir, exist_ok=True)
                    
                    # Procesar chunk individual
                    if not self._synthesize_chunk(chunk, model_path, temp_file):
                        print(f"Error al procesar chunk {i+1} de {len(chunks)}")
                        continue
                    
                    if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                        temp_files.append(temp_file)
                
                # Combinar archivos de audio
                if temp_files:
                    try:
                        with wave.open(temp_files[0], 'rb') as first:
                            params = first.getparams()
                            with wave.open(output_path, 'wb') as outfile:
                                outfile.setparams(params)
                                outfile.writeframes(first.readframes(first.getnframes()))
                                
                                for temp_file in temp_files[1:]:
                                    with wave.open(temp_file, 'rb') as infile:
                                        if infile.getparams() == params:
                                            outfile.writeframes(infile.readframes(infile.getnframes()))
                                        else:
                                            print(f"Advertencia: Parámetros diferentes en {temp_file}, saltando...")
                        
                        # Limpiar archivos temporales
                        for temp_file in temp_files:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        
                        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
                    except Exception as e:
                        print(f"Error al combinar chunks de audio: {e}")
                        import traceback
                        traceback.print_exc()
                        return False
                else:
                    print("Error: No se generaron chunks de audio")
                    return False
            else:
                # Solo un chunk, procesar normalmente
                return self._synthesize_chunk(text, model_path, output_path)
        else:
            # Texto corto, procesar directamente
            return self._synthesize_chunk(text, model_path, output_path)
    
    def _synthesize_chunk(self, text: str, model_path: str, output_path: str) -> bool:
        """
        Sintetiza un chunk de texto usando Piper.
        
        Args:
            text: Texto a sintetizar
            model_path: Ruta al modelo de Piper
            output_path: Ruta donde guardar el archivo WAV
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        try:
            # Asegurar que el directorio existe
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Ejecutar Piper con parámetros de síntesis configurables
            cmd = [
                self.piper_path,
                "--model", model_path,
                "--output_file", output_path,
                "--length_scale", str(self.length_scale),
                "--noise_scale", str(self.noise_scale),
                "--noise_w", str(self.noise_w),
                "--sentence_silence", str(self.sentence_silence),
                "--speaker", str(self.speaker),
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=text, timeout=300)
            
            if process.returncode != 0:
                print(f"Error al ejecutar Piper: {stderr}")
                return False
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        
        except subprocess.TimeoutExpired:
            print("Timeout al ejecutar Piper TTS")
            return False
        except Exception as e:
            print(f"Error al sintetizar con Piper: {e}")
            import traceback
            traceback.print_exc()
            return False


class gTTSEngine(TTSEngine):
    """
    Motor TTS usando Google Text-to-Speech (requiere internet).
    """
    
    def __init__(self, lang: str = "es", slow: bool = False):
        """
        Inicializa el motor gTTS.
        
        Args:
            lang: Código de idioma (default: "es" para español)
            slow: Si True, habla más lento (default: False)
        """
        self.lang = lang
        self.slow = slow
    
    def is_available(self) -> bool:
        """gTTS siempre está disponible si está instalado."""
        try:
            from gtts import gTTS
            return True
        except ImportError:
            return False
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Sintetiza texto usando Google TTS.
        
        Args:
            text: Texto a sintetizar
            output_path: Ruta donde guardar el archivo MP3
        """
        try:
            tts = gTTS(text=text, lang=self.lang, slow=self.slow)
            # gTTS guarda en MP3, convertir a WAV si es necesario
            if output_path.endswith('.wav'):
                # Guardar temporalmente como MP3 y convertir
                temp_mp3 = output_path.replace('.wav', '.mp3')
                tts.save(temp_mp3)
                
                # Convertir MP3 a WAV usando ffmpeg si está disponible
                try:
                    subprocess.run(
                        ["ffmpeg", "-i", temp_mp3, output_path, "-y"],
                        capture_output=True,
                        check=True,
                        timeout=60
                    )
                    os.remove(temp_mp3)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Si ffmpeg no está disponible, renombrar el MP3
                    os.rename(temp_mp3, output_path.replace('.wav', '.mp3'))
                    print(f"Advertencia: gTTS genera MP3, no WAV. Archivo guardado como: {output_path.replace('.wav', '.mp3')}")
                    return False
            else:
                tts.save(output_path)
            
            return os.path.exists(output_path)
        
        except Exception as e:
            print(f"Error al sintetizar con gTTS: {e}")
            return False


class XTTSEngine(TTSEngine):
    """
    Motor TTS usando Coqui XTTS v2 (clonación de voz, multilingüe).
    Requiere: speaker_wav (ruta a audio de referencia) o speaker (nombre de voz Coqui).
    """

    XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
    # Voces Coqui por defecto por idioma (built-in, sin clonación)
    _DEFAULT_SPEAKERS = {
        "es": "Ana Florence",
        "en": "Ana Florence",
        "fr": "Ana Florence",
        "de": "Ana Florence",
        "it": "Ana Florence",
        "pt": "Ana Florence",
    }
    _MAX_CHUNK_LENGTH = 500  # XTTS funciona mejor con chunks cortos

    def __init__(
        self,
        lang: str = "es",
        speaker_wav: Optional[str] = None,
        speaker: Optional[str] = None,
        use_cuda: bool = True,
        max_chunk_length: int = 500,
    ):
        """
        Inicializa el motor XTTS.

        Args:
            lang: Código de idioma (es, en, fr, de, it, pt, etc.)
            speaker_wav: Ruta a archivo WAV de referencia para clonar voz (~3+ segundos)
            speaker: Nombre de voz Coqui built-in (ej: "Ana Florence"). Si speaker_wav está definido, se ignora.
            use_cuda: Usar GPU si está disponible
            max_chunk_length: Máximo de caracteres por chunk (default 500)
        """
        self.lang = self._map_lang(lang)
        self.speaker_wav = speaker_wav or os.environ.get("XTTS_SPEAKER_WAV")
        self.speaker = speaker or os.environ.get("XTTS_SPEAKER")
        self.use_cuda = use_cuda
        self.max_chunk_length = max_chunk_length or self._MAX_CHUNK_LENGTH
        self._tts = None

    @staticmethod
    def _map_lang(lang: str) -> str:
        """Mapea códigos de idioma al formato XTTS (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko)."""
        m = {"es": "es", "en": "en", "fr": "fr", "de": "de", "it": "it", "pt": "pt"}
        return m.get(lang.lower(), lang)

    def _get_tts(self):
        """Carga el modelo XTTS de forma lazy."""
        if self._tts is None:
            try:
                from TTS.api import TTS
            except ImportError:
                raise ImportError(
                    "Coqui TTS no está instalado. Instala con: pip install coqui-tts"
                )
            gpu = self.use_cuda
            try:
                import torch
                gpu = gpu and torch.cuda.is_available()
            except ImportError:
                gpu = False
            self._tts = TTS(self.XTTS_MODEL, gpu=gpu)
        return self._tts

    def is_available(self) -> bool:
        """Verifica si XTTS está disponible."""
        try:
            self._get_tts()
            return True
        except Exception as e:
            import sys
            import traceback
            print(f"XTTS no disponible: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False

    def _resolve_speaker(self) -> tuple:
        """
        Resuelve speaker_wav o speaker.
        Returns: (speaker_wav_list or None, speaker_name or None)
        """
        wav = self.speaker_wav
        name = self.speaker

        if wav and os.path.isfile(wav):
            return ([wav], None)
        if wav:
            paths = [p.strip() for p in wav.split(",") if p.strip()]
            valid = [p for p in paths if os.path.isfile(p)]
            if valid:
                return (valid, None)
            # No es ruta válida: tratar como nombre de voz built-in (ej: "Ana Florence")
            return (None, wav)

        return (None, name or self._DEFAULT_SPEAKERS.get(self.lang, "Ana Florence"))

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Sintetiza texto usando XTTS.
        Divide en chunks si es necesario.
        """
        if not text.strip():
            return False

        speaker_wav_list, speaker_name = self._resolve_speaker()
        if not speaker_wav_list and not speaker_name:
            raise ValueError(
                "XTTS requiere --voice con ruta a WAV de referencia para clonar voz, "
                "o configura XTTS_SPEAKER con el nombre de una voz Coqui (ej: Ana Florence)."
            )

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        if len(text) <= self.max_chunk_length:
            return self._synthesize_chunk(
                text, output_path, speaker_wav_list, speaker_name
            )

        # Dividir en chunks por oraciones
        import re
        try:
            import nltk
            try:
                sentences = nltk.sent_tokenize(text)
            except (LookupError, Exception):
                sentences = re.split(r'[.!?]+\s+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
        except ImportError:
            sentences = re.split(r'[.!?]+\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current = []
        length = 0
        for s in sentences:
            if length + len(s) > self.max_chunk_length and current:
                chunks.append(" ".join(current))
                current = [s]
                length = len(s)
            else:
                current.append(s)
                length += len(s) + 1
        if current:
            chunks.append(" ".join(current))

        if len(chunks) == 1:
            return self._synthesize_chunk(
                text, output_path, speaker_wav_list, speaker_name
            )

        import wave
        temp_files = []
        for i, chunk in enumerate(chunks):
            tp = output_path.replace(".wav", f"_xtts_temp_{i}.wav")
            ok = self._synthesize_chunk(
                chunk, tp, speaker_wav_list, speaker_name
            )
            if ok and os.path.exists(tp) and os.path.getsize(tp) > 0:
                temp_files.append(tp)

        if not temp_files:
            return False

        try:
            with wave.open(temp_files[0], "rb") as first:
                params = first.getparams()
                with wave.open(output_path, "wb") as out:
                    out.setparams(params)
                    out.writeframes(first.readframes(first.getnframes()))
                    for tf in temp_files[1:]:
                        with wave.open(tf, "rb") as inf:
                            if inf.getparams() == params:
                                out.writeframes(inf.readframes(inf.getnframes()))
            for tf in temp_files:
                if os.path.exists(tf):
                    os.remove(tf)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            print(f"Error al combinar chunks XTTS: {e}")
            for tf in temp_files:
                if os.path.exists(tf):
                    try:
                        os.remove(tf)
                    except OSError:
                        pass
            return False

    def _synthesize_chunk(
        self,
        text: str,
        output_path: str,
        speaker_wav_list: Optional[list],
        speaker_name: Optional[str],
    ) -> bool:
        try:
            tts = self._get_tts()
            kwargs = {
                "text": text.strip(),
                "file_path": output_path,
                "language": self.lang,
                "split_sentences": True,
            }
            if speaker_wav_list:
                kwargs["speaker_wav"] = speaker_wav_list
            else:
                kwargs["speaker"] = speaker_name

            tts.tts_to_file(**kwargs)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            print(f"Error al sintetizar con XTTS: {e}")
            import traceback
            traceback.print_exc()
            return False


def create_tts_engine(engine_name: str, **kwargs) -> TTSEngine:
    """
    Factory function para crear instancias de motores TTS.
    
    Args:
        engine_name: Nombre del motor ("piper", "gtts", "xtts")
        **kwargs: Argumentos adicionales para el motor específico
    
    Returns:
        Instancia del motor TTS
    
    Raises:
        ValueError: Si el nombre del motor no es reconocido
    """
    engine_name_lower = engine_name.lower()

    if engine_name_lower == "piper":
        return PiperTTS(
            piper_path=kwargs.get("piper_path"),
            voice=kwargs.get("voice"),
            lang=kwargs.get("lang", "es"),
            max_chunk_length=kwargs.get("max_chunk_length", 2000),
            length_scale=kwargs.get("length_scale", 1.0),
            noise_scale=kwargs.get("noise_scale", 0.667),
            noise_w=kwargs.get("noise_w", 0.8),
            sentence_silence=kwargs.get("sentence_silence", 0.3),
            speaker=kwargs.get("speaker", 0),
        )
    elif engine_name_lower == "gtts":
        return gTTSEngine(
            lang=kwargs.get("lang", "es"),
            slow=kwargs.get("slow", False)
        )
    elif engine_name_lower == "xtts":
        return XTTSEngine(
            lang=kwargs.get("lang", "es"),
            speaker_wav=kwargs.get("speaker_wav") or kwargs.get("voice"),
            speaker=kwargs.get("speaker"),
            use_cuda=kwargs.get("use_cuda", True),
            max_chunk_length=kwargs.get("max_chunk_length", 500)
        )
    else:
        raise ValueError(
            f"Motor TTS desconocido: {engine_name}. "
            f"Opciones disponibles: piper, gtts, xtts"
        )
