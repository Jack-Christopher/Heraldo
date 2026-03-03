"""
Módulo para procesamiento de texto con IA usando Ollama o DeepSeek.
Fase 2 del sistema Heraldo.
"""

import time
import requests
from typing import Optional
from .utils import clear_memory


# Estilos de procesamiento: define cómo la IA debe adaptar el contenido para audiolibro
AI_STYLE_PROMPTS = {
    "divulgacion": (
        "Eres un narrador académico y divulgador. Tu objetivo es que el texto se entienda "
        "bien al escucharlo, incluso mejor que al leerlo. Responde únicamente en español. "
        "Tu salida debe ser solo el texto listo para leer en voz alta, sin preámbulos ni "
        "comentarios tipo 'He reescrito lo siguiente' o similar. "
        "1. AÑADE contexto cuando ayude: términos técnicos o poco comunes (breve explicación "
        "entre paréntesis), referencias históricas o personajes (una frase de contexto), "
        "citas en latín u otro idioma (traducción o glosa entre paréntesis). "
        "2. OMITE: créditos de descarga, pies de página repetitivos, referencias de fuente "
        "si no aportan al contenido. "
        "3. Si es un ÍNDICE, sustituye por: 'El contenido de este libro consta de las siguientes "
        "partes:' y enumera solo los títulos principales. "
        "4. Parafrasear oraciones complejas para que sean fluidas. Separa las ideas con puntos. "
        "5. Mantén la fidelidad al contenido con un tono ameno."
    ),
    "narrativo": (
        "Eres un narrador experto. Adapta el texto para una experiencia de audiolibro envolvente. "
        "Responde únicamente en español. Tu salida debe ser solo el texto listo para leer en voz "
        "alta, sin preámbulos ni comentarios. "
        "1. ENFÓCATE en la experiencia y la narrativa: fluidez, ritmo, inmersión. Las descripciones "
        "y los diálogos deben sonar naturales al oído. "
        "2. Preserva el tono, la atmósfera y la tensión dramática. Evita interrumpir la inmersión "
        "con explicaciones innecesarias. "
        "3. OMITE: pies de página, referencias, créditos. "
        "4. Si hay citas en otro idioma, tradúcelas o glosa brevemente entre paréntesis. "
        "5. Mantén oraciones fluidas. Separa las ideas con puntos para pausas naturales."
    ),
    "filosofia": (
        "Eres un divulgador de filosofía y pensamiento. Adapta el texto para que se entienda "
        "perfectamente al escucharlo. Responde únicamente en español. Tu salida debe ser solo "
        "el texto listo para leer en voz alta, sin preámbulos. "
        "1. EXPLICA y da contexto: términos filosóficos (ej: 'a priori', 'dialéctica', 'eudaimonia') "
        "deben desarrollarse con una breve definición o ejemplo entre paréntesis la primera vez "
        "que aparezcan. "
        "2. Citas en griego, latín o alemán: tradúcelas y, si es útil, añade una glosa breve. "
        "3. Referencias a obras (ej: 'Eth. Nic. I 8'): conviértelas en referencias comprensibles "
        "(ej: 'como dice Aristóteles en la Ética a Nicómaco'). "
        "4. Desarrolla los conceptos complejos paso a paso. No asumas que el oyente conoce "
        "la terminología. "
        "5. OMITE pies de página, notas técnicas que no aporten. Mantén la fidelidad al argumento."
    ),
    "ensayo": (
        "Eres un divulgador de ensayos y textos reflexivos. Adapta el contenido para audiolibro. "
        "Responde únicamente en español. Tu salida debe ser solo el texto listo para leer en voz "
        "alta, sin preámbulos. "
        "1. Da contexto y explica conceptos complejos cuando sea necesario. Aclara términos "
        "abstractos o especializados entre paréntesis. "
        "2. Preserva la estructura argumentativa y el tono del autor. "
        "3. Citas en otros idiomas: traduce o glosa brevemente. Referencias a obras: hazlas "
        " comprensibles para quien escucha. "
        "4. Separa las ideas con puntos. Cada idea debe terminar con un punto. "
        "5. OMITE referencias de fuente irrelevantes. Mantén la profundidad del contenido."
    ),
    "tecnico": (
        "Eres un divulgador técnico. Adapta el texto para audiolibro manteniendo precisión. "
        "Responde únicamente en español. Tu salida debe ser solo el texto listo para leer en voz "
        "alta, sin preámbulos. "
        "1. Explica jerga y siglas la primera vez que aparezcan (ej: 'API, interfaz de programación "
        "de aplicaciones'). "
        "2. Convierte listas o tablas en frases fluidas cuando sea posible. "
        "3. Mantén la precisión técnica. No simplifiques de más ni pierdas información clave. "
        "4. OMITE código fuente largo; resume su función en una frase si es relevante. "
        "5. Separa las ideas con puntos para pausas naturales."
    ),
    "poesia": (
        "Eres un adaptador de textos poéticos para audiolibro. Responde únicamente en español. "
        "Tu salida debe ser solo el texto listo para leer en voz alta, sin preámbulos. "
        "1. PRESERVA el ritmo, la musicalidad y las imágenes del poema. Cambia lo mínimo necesario. "
        "2. Si hay versos en otro idioma, tradúcelos o glosa entre paréntesis. "
        "3. Respeta la estructura: estrofas, saltos de línea, pausas. Indica pausas largas con "
        " puntos y aparte. "
        "4. No añadas explicaciones que rompan la atmósfera. "
        "5. OMITE numeración de versos, notas al pie. Mantén la fuerza evocadora del original."
    ),
}


def get_ai_style_prompt(style: str) -> str:
    """
    Devuelve el prompt del sistema para un estilo de contenido.

    Args:
        style: Uno de: divulgacion, narrativo, filosofia, ensayo, tecnico, poesia

    Returns:
        Prompt del sistema. Si el estilo no existe, devuelve 'divulgacion'.
    """
    return AI_STYLE_PROMPTS.get(style.lower(), AI_STYLE_PROMPTS["divulgacion"])


class OllamaProcessor:
    """
    Procesador de texto usando la API local de Ollama.
    Parafrasea y enriquece el texto para lectura en voz alta.
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3,
        timeout: int = 600,
        num_predict: int = 4000,
        num_ctx: int = 8192,
        ai_style: str = "divulgacion",
    ):
        """
        Inicializa el procesador de Ollama.

        Args:
            model: Nombre del modelo de Ollama a usar
            base_url: URL base de la API de Ollama (default: http://localhost:11434)
            max_retries: Número máximo de reintentos en caso de error
            timeout: Timeout en segundos para las peticiones (default: 600 = 10 minutos)
            num_predict: Número máximo de tokens a generar (default: 4000)
            num_ctx: Tamaño del contexto en tokens (default: 8192)
            ai_style: Estilo de procesamiento: divulgacion, narrativo, filosofia, ensayo, tecnico, poesia
        """
        self.model = model
        self.system_prompt = get_ai_style_prompt(ai_style)
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.timeout = timeout
        self.num_predict = num_predict
        self.num_ctx = num_ctx
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
        
        prompt = f"{self.system_prompt}\n\nTexto a procesar:\n\n{text_block}"
        
        # Calcular tokens aproximados del prompt para ajustar num_ctx si es necesario
        from .utils import count_tokens
        prompt_tokens = count_tokens(prompt)
        
        # Ajustar num_ctx dinámicamente si el prompt es muy grande
        # Dejar espacio para la respuesta (num_predict)
        effective_num_ctx = max(self.num_ctx, prompt_tokens + self.num_predict + 512)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": self.num_predict,  # Limitar tokens de respuesta
                "num_ctx": effective_num_ctx,  # Contexto suficiente
            }
        }
        
        try:
            # Mostrar información de diagnóstico en el primer intento
            if retry_count == 0:
                print(f"  Procesando bloque: ~{prompt_tokens} tokens de entrada, "
                      f"máximo {self.num_predict} tokens de salida, "
                      f"timeout: {self.timeout}s")
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
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
            print(f"  Tamaño del bloque: ~{len(text_block)} caracteres, ~{count_tokens(text_block)} tokens")
            print(f"  Timeout configurado: {self.timeout} segundos")
            print(f"  Sugerencia: Considera reducir --block-size o aumentar el timeout")
            
            if retry_count < self.max_retries - 1:
                # Backoff exponencial
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            else:
                print("Error: Se agotaron los reintentos por timeout")
                print(f"  El bloque puede ser demasiado grande. Considera:")
                print(f"  - Reducir --block-size (actualmente ~{count_tokens(text_block)} tokens)")
                print(f"  - Usar un modelo más rápido")
                print(f"  - Verificar que Ollama esté funcionando correctamente")
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


class DeepSeekProcessor:
    """
    Procesador de texto usando la API de DeepSeek (OpenAI-compatible).
    Parafrasea y enriquece el texto para lectura en voz alta.
    Misma interfaz que OllamaProcessor: process_block(text_block, retry_count=0) -> Optional[str].
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        max_retries: int = 3,
        timeout: int = 600,
        max_tokens: int = 4000,
        ai_style: str = "divulgacion",
    ):
        """
        Inicializa el procesador de DeepSeek.

        Args:
            api_key: Token de API de DeepSeek (Bearer).
            model: Modelo a usar (default: deepseek-chat).
            base_url: URL base de la API (default: https://api.deepseek.com).
            max_retries: Número máximo de reintentos.
            timeout: Timeout en segundos para las peticiones.
            max_tokens: Máximo de tokens a generar en la respuesta.
            ai_style: Estilo de procesamiento: divulgacion, narrativo, filosofia, ensayo, tecnico, poesia
        """
        self.api_key = api_key
        self.system_prompt = get_ai_style_prompt(ai_style)
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.api_url = f"{self.base_url}/v1/chat/completions"

    def process_block(
        self,
        text_block: str,
        retry_count: int = 0,
    ) -> Optional[str]:
        """
        Procesa un bloque de texto con la API de DeepSeek.

        Args:
            text_block: Bloque de texto a procesar.
            retry_count: Número de intentos actual (para recursión).

        Returns:
            Texto procesado/enriquecido o None si falla después de todos los reintentos.
        """
        from .utils import count_tokens, parse_deepseek_response

        prompt_tokens = count_tokens(text_block)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Texto a procesar:\n\n{text_block}"},
            ],
            "temperature": 0.7,
            "max_tokens": self.max_tokens,
        }

        try:
            if retry_count == 0:
                print(
                    f"  Procesando bloque: ~{prompt_tokens} tokens de entrada, "
                    f"máximo {self.max_tokens} tokens de salida, timeout: {self.timeout}s"
                )

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            ok, processed_text, error_message = parse_deepseek_response(response)
            if not ok:
                print(f"Error API DeepSeek: {error_message}")
                if 400 <= response.status_code < 500:
                    return None  # No reintentar en 4xx (p. ej. 402 Payment Required)
                raise ValueError(error_message or f"HTTP {response.status_code}")
            if not processed_text:
                raise ValueError("DeepSeek devolvió una respuesta vacía")

            clear_memory()
            return processed_text

        except requests.exceptions.Timeout:
            error_msg = (
                f"Timeout al procesar bloque (intento {retry_count + 1}/{self.max_retries})"
            )
            print(error_msg)
            print(
                f"  Tamaño del bloque: ~{len(text_block)} caracteres, ~{count_tokens(text_block)} tokens"
            )
            if retry_count < self.max_retries - 1:
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            return None

        except requests.exceptions.RequestException as e:
            err_display = str(e)
            if getattr(e, "response", None) is not None:
                _, _, api_err = parse_deepseek_response(e.response)
                if api_err:
                    err_display = api_err
            print(
                f"Error al procesar bloque (intento {retry_count + 1}/{self.max_retries}): {err_display}"
            )
            # No reintentar en errores 4xx (p. ej. 402 Payment Required, 401 Unauthorized)
            if getattr(e, "response", None) is not None and 400 <= e.response.status_code < 500:
                return None
            if retry_count < self.max_retries - 1:
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            return None

        except Exception as e:
            print(
                f"Error inesperado al procesar bloque (intento {retry_count + 1}/{self.max_retries}): {e}"
            )
            if retry_count < self.max_retries - 1:
                wait_time = 2 ** retry_count
                print(f"Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
                return self.process_block(text_block, retry_count + 1)
            return None
