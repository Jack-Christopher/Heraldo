"""
Módulo para procesamiento de texto con IA usando Ollama.
Fase 2 del sistema Heraldo.
"""

import time
import requests
from typing import Optional
from .utils import clear_memory


class OllamaProcessor:
    """
    Procesador de texto usando la API local de Ollama.
    Parafrasea y enriquece el texto para lectura en voz alta.
    """
    
    SYSTEM_PROMPT = (
        "Eres un narrador académico y divulgador. Tu tarea es reescribir el texto "
        "recibido para ser leído en voz alta. Debes: "
        "1. Parafrasear oraciones complejas para que sean fluidas. "
        "2. Si detectas un término técnico o poco común, añade una breve explicación "
        "entre paréntesis. "
        "3. Si hay una referencia histórica, añade una frase de contexto. "
        "4. Mantén la fidelidad al contenido original pero con un tono ameno. "
        "5. IMPORTANTE: Separa las ideas con puntos. Cada idea o concepto debe terminar "
        "con un punto antes de pasar a la siguiente. No escribas párrafos continuos sin "
        "puntuación adecuada. Usa puntos para crear pausas naturales en la lectura."
    )
    
    def __init__(
        self, 
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3
    ):
        """
        Inicializa el procesador de Ollama.
        
        Args:
            model: Nombre del modelo de Ollama a usar
            base_url: URL base de la API de Ollama (default: http://localhost:11434)
            max_retries: Número máximo de reintentos en caso de error
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.api_url = f"{self.base_url}/api/generate"
    
    def _check_ollama_connection(self) -> bool:
        """
        Verifica que Ollama esté disponible y el modelo exista.
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            # Verificar que Ollama está corriendo
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Verificar que el modelo existe
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            if self.model not in model_names:
                print(f"Advertencia: El modelo '{self.model}' no está disponible.")
                print(f"Modelos disponibles: {', '.join(model_names[:5])}")
                return False
            
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error al conectar con Ollama: {e}")
            return False
    
    def process_block(
        self, 
        text_block: str, 
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Procesa un bloque de texto con Ollama.
        
        Args:
            text_block: Bloque de texto a procesar
            retry_count: Número de intentos actual (para recursión)
        
        Returns:
            Texto procesado/enriquecido o None si falla después de todos los reintentos
        """
        if retry_count == 0:
            # Verificar conexión solo en el primer intento
            if not self._check_ollama_connection():
                raise ConnectionError(
                    f"No se pudo conectar con Ollama en {self.base_url} "
                    f"o el modelo '{self.model}' no está disponible."
                )
        
        prompt = f"{self.SYSTEM_PROMPT}\n\nTexto a procesar:\n\n{text_block}"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300  # 5 minutos de timeout para bloques grandes
            )
            response.raise_for_status()
            
            result = response.json()
            processed_text = result.get("response", "").strip()
            
            if not processed_text:
                raise ValueError("Ollama devolvió una respuesta vacía")
            
            # Liberar memoria después de procesar
            clear_memory()
            
            return processed_text
        
        except requests.exceptions.Timeout:
            error_msg = f"Timeout al procesar bloque (intento {retry_count + 1}/{self.max_retries})"
            print(error_msg)
            
            if retry_count < self.max_retries - 1:
                # Backoff exponencial
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            else:
                print("Error: Se agotaron los reintentos por timeout")
                return None
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión al procesar bloque (intento {retry_count + 1}/{self.max_retries}): {e}"
            print(error_msg)
            
            if retry_count < self.max_retries - 1:
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            else:
                print("Error: Se agotaron los reintentos por error de conexión")
                return None
        
        except Exception as e:
            error_msg = f"Error inesperado al procesar bloque (intento {retry_count + 1}/{self.max_retries}): {e}"
            print(error_msg)
            
            if retry_count < self.max_retries - 1:
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            else:
                print("Error: Se agotaron los reintentos por error inesperado")
                return None
