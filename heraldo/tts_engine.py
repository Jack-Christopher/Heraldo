"""
Módulo para conversión de texto a voz (TTS) usando múltiples motores.
Fase 4 del sistema Heraldo.
"""

import os
import subprocess
from abc import ABC, abstractmethod
from typing import Optional
from gtts import gTTS
import pyttsx3


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
    
    def __init__(self, piper_path: Optional[str] = None, voice: Optional[str] = None, lang: str = "es"):
        """
        Inicializa el motor Piper TTS.
        
        Args:
            piper_path: Ruta al ejecutable de Piper (o None para usar PATH)
            voice: Nombre del modelo de voz (ej: es_ES-davefx-medium)
            lang: Código de idioma para seleccionar voz por defecto (default: "es")
        """
        self.piper_path = piper_path or os.environ.get("PIPER_PATH", "piper-bin")
        self.voice = voice or os.environ.get("PIPER_VOICE")
        
        # Si voice no está especificado, usar uno por defecto basado en el idioma
        if not self.voice:
            # Modelos por idioma (priorizando español latinoamericano)
            lang_voices = {
                'es': 'es_MX-ald-medium',  # Español - México (más neutral)
                'en': 'en_US-lessac-medium',  # Inglés - US
                'fr': 'fr_FR-upmc-medium',  # Francés
                'de': 'de_DE-thorsten-medium',  # Alemán
                'it': 'it_IT-riccardo-medium',  # Italiano
                'pt': 'pt_BR-faber-medium',  # Portugués - Brasil
            }
            # Modelos alternativos si el principal no está disponible
            lang_voices_alt = {
                'es': ['es_MX-ald-medium', 'es_ES-davefx-medium', 'es_AR-tango-medium'],
                'en': ['en_US-lessac-medium', 'en_GB-alba-medium'],
                'fr': ['fr_FR-upmc-medium'],
                'de': ['de_DE-thorsten-medium'],
                'it': ['it_IT-riccardo-medium'],
                'pt': ['pt_BR-faber-medium'],
            }
            
            # Usar el modelo principal para el idioma, o el primero de la lista
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
        
        # Construir ruta al modelo (asumiendo formato estándar)
        # El usuario debe tener el modelo descargado
        model_path = self.voice
        
        # Si la ruta no existe, intentar varias ubicaciones comunes
        if not os.path.exists(model_path):
            # Intentar con extensión .onnx
            if not model_path.endswith('.onnx'):
                model_path_onnx = f"{self.voice}.onnx"
                if os.path.exists(model_path_onnx):
                    model_path = model_path_onnx
                else:
                    # Intentar en directorio de modelos común
                    possible_paths = [
                        os.path.join(os.path.expanduser("~"), ".local", "share", "piper", "voices", self.voice, f"{self.voice}.onnx"),
                        os.path.join(".", "models", f"{self.voice}.onnx"),
                        os.path.join(".", f"{self.voice}.onnx"),
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            model_path = path
                            break
                    else:
                        # Si no se encuentra, usar el nombre tal cual (piper puede buscarlo)
                        model_path = self.voice
        
        try:
            # Ejecutar Piper
            # Formato: piper --model model.onnx --output_file output.wav
            cmd = [
                self.piper_path,
                "--model", model_path,
                "--output_file", output_path
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
            
            return os.path.exists(output_path)
        
        except subprocess.TimeoutExpired:
            print("Timeout al ejecutar Piper TTS")
            return False
        except Exception as e:
            print(f"Error al sintetizar con Piper: {e}")
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


class Pyttsx3Engine(TTSEngine):
    """
    Motor TTS usando pyttsx3 (offline, multiplataforma).
    """
    
    def __init__(self, voice_id: Optional[int] = None, rate: int = 150, sentences_per_chunk: int = 10, lang: str = "es"):
        """
        Inicializa el motor pyttsx3.
        
        Args:
            voice_id: ID de la voz a usar (None para buscar voz en el idioma especificado)
            rate: Velocidad de habla en palabras por minuto (default: 150)
            sentences_per_chunk: Número de oraciones por chunk (default: 10)
            lang: Código de idioma para buscar voz (default: "es" para español)
        """
        self.voice_id = voice_id
        self.rate = rate
        self.sentences_per_chunk = sentences_per_chunk
        self.lang = lang
        self.engine = None
    
    def _initialize_engine(self):
        """Inicializa el motor pyttsx3."""
        if self.engine is None:
            try:
                self.engine = pyttsx3.init()
                voices = self.engine.getProperty('voices')
                
                # Si se especificó un voice_id, usarlo
                if self.voice_id is not None:
                    if self.voice_id < len(voices):
                        self.engine.setProperty('voice', voices[self.voice_id].id)
                else:
                    # Buscar voz en el idioma especificado
                    voice_found = False
                    lang_code = self.lang.lower()
                    
                    # PRIMERO buscar por nombre (más confiable que ID)
                    lang_keywords = {
                        'es': ['spanish', 'español'],
                        'en': ['english', 'inglés'],
                        'fr': ['french', 'francés'],
                        'de': ['german', 'alemán'],
                        'it': ['italian', 'italiano'],
                        'pt': ['portuguese', 'portugués']
                    }
                    keywords = lang_keywords.get(lang_code, lang_keywords['es'])
                    
                    for voice in voices:
                        voice_name_lower = voice.name.lower()
                        if any(keyword in voice_name_lower for keyword in keywords):
                            self.engine.setProperty('voice', voice.id)
                            voice_found = True
                            break
                    
                    # Si no se encontró por nombre, buscar por ID
                    if not voice_found:
                        # Buscar patrones específicos en el ID: "roa/es", "roa/es-", etc.
                        for voice in voices:
                            voice_id_lower = voice.id.lower()
                            
                            # Para español, buscar específicamente "roa/es" (no "/es" que coincide con "/en")
                            if lang_code == 'es':
                                if 'roa/es' in voice_id_lower:
                                    self.engine.setProperty('voice', voice.id)
                                    voice_found = True
                                    break
                            else:
                                # Para otros idiomas
                                if f'roa/{lang_code}' in voice_id_lower or f'gmw/{lang_code}' in voice_id_lower:
                                    self.engine.setProperty('voice', voice.id)
                                    voice_found = True
                                    break
                    
                    # Si no se encontró, usar la primera voz disponible
                    if not voice_found and voices:
                        self.engine.setProperty('voice', voices[0].id)
                
                self.engine.setProperty('rate', self.rate)
            except Exception as e:
                raise RuntimeError(f"No se pudo inicializar pyttsx3: {e}")
    
    def is_available(self) -> bool:
        """Verifica si pyttsx3 está disponible."""
        try:
            self._initialize_engine()
            return self.engine is not None
        except Exception:
            return False
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Sintetiza texto usando pyttsx3.
        
        Args:
            text: Texto a sintetizar
            output_path: Ruta donde guardar el archivo WAV
        """
        try:
            self._initialize_engine()
            
            # Establecer la voz correcta antes de sintetizar (pyttsx3 puede perder la configuración)
            if self.voice_id is None:
                voices = self.engine.getProperty('voices')
                lang_code = self.lang.lower()
                lang_keywords = {
                    'es': ['spanish', 'español'],
                    'en': ['english', 'inglés'],
                    'fr': ['french', 'francés'],
                    'de': ['german', 'alemán'],
                    'it': ['italian', 'italiano'],
                    'pt': ['portuguese', 'portuguese']
                }
                keywords = lang_keywords.get(lang_code, lang_keywords['es'])
                
                for voice in voices:
                    voice_name_lower = voice.name.lower()
                    if any(keyword in voice_name_lower for keyword in keywords):
                        self.engine.setProperty('voice', voice.id)
                        break
                else:
                    # Si no se encontró por nombre, buscar por ID
                    for voice in voices:
                        voice_id_lower = voice.id.lower()
                        if lang_code == 'es' and 'roa/es' in voice_id_lower:
                            self.engine.setProperty('voice', voice.id)
                            break
                        elif f'roa/{lang_code}' in voice_id_lower or f'gmw/{lang_code}' in voice_id_lower:
                            self.engine.setProperty('voice', voice.id)
                            break
            
            # Asegurar que el directorio existe
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Dividir texto en chunks de oraciones (pyttsx3 funciona mejor con textos cortos)
            import re
            import nltk
            
            # Intentar usar nltk para tokenización
            try:
                sentences = nltk.sent_tokenize(text)
            except LookupError:
                # Si falta punkt_tab, descargarlo automáticamente
                try:
                    nltk.download('punkt_tab', quiet=True)
                    sentences = nltk.sent_tokenize(text)
                except:
                    # Fallback: división simple por puntuación y longitud
                    sentences = re.split(r'[.!?]+\s+', text)
                    sentences = [s.strip() for s in sentences if s.strip()]
                    # Si no hay puntos, dividir por longitud aproximada (150 caracteres = ~1 oración)
                    if len(sentences) == 1 and len(text) > 200:
                        # Dividir por espacios cada ~150 caracteres
                        words = text.split()
                        current_sentence = []
                        sentences = []
                        current_length = 0
                        for word in words:
                            current_sentence.append(word)
                            current_length += len(word) + 1
                            if current_length > 150:
                                sentences.append(' '.join(current_sentence))
                                current_sentence = []
                                current_length = 0
                        if current_sentence:
                            sentences.append(' '.join(current_sentence))
            except:
                # Fallback final: división simple por puntuación
                sentences = re.split(r'[.!?]+\s+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
                # Si aún no hay divisiones, dividir por longitud
                if len(sentences) == 1 and len(text) > 200:
                    words = text.split()
                    current_sentence = []
                    sentences = []
                    current_length = 0
                    for word in words:
                        current_sentence.append(word)
                        current_length += len(word) + 1
                        if current_length > 150:
                            sentences.append(' '.join(current_sentence))
                            current_sentence = []
                            current_length = 0
                    if current_sentence:
                        sentences.append(' '.join(current_sentence))
            
            # Dividir en chunks del tamaño especificado
            chunks = []
            for i in range(0, len(sentences), self.sentences_per_chunk):
                chunk = ' '.join(sentences[i:i + self.sentences_per_chunk])
                if chunk.strip():
                    # Asegurar que termina con puntuación
                    if not re.search(r'[.!?]$', chunk.strip()):
                        chunk += '.'
                    chunks.append(chunk.strip())
            
            # Si hay múltiples chunks o texto largo, procesar por chunks
            if len(chunks) > 1:
                # Procesar cada chunk y combinar
                import wave
                temp_files = []
                
                for i, chunk in enumerate(chunks):
                    temp_file = output_path.replace('.wav', f'_temp_{i}.wav')
                    # Asegurar que el directorio del archivo temporal existe
                    temp_dir = os.path.dirname(temp_file)
                    if temp_dir and not os.path.exists(temp_dir):
                        os.makedirs(temp_dir, exist_ok=True)
                    
                    # Establecer la voz correcta antes de cada chunk
                    if self.voice_id is None:
                        voices = self.engine.getProperty('voices')
                        lang_code = self.lang.lower()
                        lang_keywords = {
                            'es': ['spanish', 'español'],
                            'en': ['english', 'inglés'],
                            'fr': ['french', 'francés'],
                            'de': ['german', 'alemán'],
                            'it': ['italian', 'italiano'],
                            'pt': ['portuguese', 'portugués']
                        }
                        keywords = lang_keywords.get(lang_code, lang_keywords['es'])
                        
                        for voice in voices:
                            voice_name_lower = voice.name.lower()
                            if any(keyword in voice_name_lower for keyword in keywords):
                                self.engine.setProperty('voice', voice.id)
                                break
                        else:
                            # Si no se encontró por nombre, buscar por ID
                            for voice in voices:
                                voice_id_lower = voice.id.lower()
                                if lang_code == 'es' and 'roa/es' in voice_id_lower:
                                    self.engine.setProperty('voice', voice.id)
                                    break
                                elif f'roa/{lang_code}' in voice_id_lower or f'gmw/{lang_code}' in voice_id_lower:
                                    self.engine.setProperty('voice', voice.id)
                                    break
                    
                    try:
                        self.engine.save_to_file(chunk, temp_file)
                        self.engine.runAndWait()
                        # Esperar un momento para que el archivo se escriba completamente
                        import time
                        time.sleep(0.5)
                        
                        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                            temp_files.append(temp_file)
                        else:
                            print(f"Advertencia: Chunk {i+1} no se generó correctamente (archivo: {temp_file})")
                    except Exception as e:
                        print(f"Error al procesar chunk {i+1}: {e}")
                
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
                                        outfile.writeframes(infile.readframes(infile.getnframes()))
                        
                        # Limpiar archivos temporales
                        for temp_file in temp_files:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                    except Exception as e:
                        print(f"Error al combinar chunks de audio: {e}")
                        return False
                else:
                    print("Error: No se generaron chunks de audio")
                    return False
            else:
                # Texto corto o un solo chunk, procesar normalmente
                self.engine.save_to_file(chunks[0] if chunks else text, output_path)
                self.engine.runAndWait()
            
            # Verificar que el archivo se creó y no está vacío
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 0:
                    return True
                else:
                    print(f"Advertencia: Archivo {output_path} se creó pero está vacío ({file_size} bytes)")
                    return False
            else:
                print(f"Advertencia: Archivo {output_path} no se creó después de runAndWait()")
                return False
        
        except Exception as e:
            print(f"Error al sintetizar con pyttsx3: {e}")
            import traceback
            traceback.print_exc()
            return False


def create_tts_engine(engine_name: str, **kwargs) -> TTSEngine:
    """
    Factory function para crear instancias de motores TTS.
    
    Args:
        engine_name: Nombre del motor ("piper", "gtts", "pyttsx3")
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
            lang=kwargs.get("lang", "es")
        )
    elif engine_name_lower == "gtts":
        return gTTSEngine(
            lang=kwargs.get("lang", "es"),
            slow=kwargs.get("slow", False)
        )
    elif engine_name_lower == "pyttsx3":
        return Pyttsx3Engine(
            voice_id=kwargs.get("voice_id"),
            rate=kwargs.get("rate", 150),
            sentences_per_chunk=kwargs.get("sentences_per_chunk", 10),
            lang=kwargs.get("lang", "es")
        )
    else:
        raise ValueError(
            f"Motor TTS desconocido: {engine_name}. "
            f"Opciones disponibles: piper, gtts, pyttsx3"
        )
