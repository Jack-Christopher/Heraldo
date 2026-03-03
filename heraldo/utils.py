"""
Utilidades generales para el sistema Heraldo.
Incluye funciones para conteo de tokens, limpieza de memoria, validación y barras de progreso.
"""

import os
import tiktoken
from typing import Optional, Tuple, Any

# Respuestas/errores de la API DeepSeek (OpenAI-compatible)
def parse_deepseek_response(response: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Interpreta la respuesta HTTP de la API de DeepSeek.

    Args:
        response: Objeto requests.Response.

    Returns:
        (ok, content, error_message): ok=True si 2xx y contenido extraído;
            ok=False con error_message legible (incl. mensaje del cuerpo JSON).
    """
    try:
        import requests
    except ImportError:
        requests = None

    if response.status_code >= 200 and response.status_code < 300:
        try:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            content = (choice.get("message", {}).get("content") or "").strip()
            return (True, content if content else None, None)
        except Exception as e:
            return (False, None, f"Respuesta OK pero no se pudo leer el contenido: {e}")
    # Error HTTP
    try:
        body = response.json()
        err = body.get("error") or {}
        api_msg = err.get("message") or err.get("code") or ""
        status = getattr(response, "status_code", None) or ""
        reason = getattr(response, "reason", "") or ""
        if api_msg:
            msg = f"{status} {reason}: {api_msg}".strip()
        else:
            msg = f"{status} {reason}".strip() or (response.text[:500] if getattr(response, "text", None) else "Error desconocido")
        return (False, None, msg)
    except Exception:
        text = getattr(response, "text", "") or ""
        status = getattr(response, "status_code", "")
        reason = getattr(response, "reason", "")
        return (False, None, f"{status} {reason}: {text[:500]}".strip())


def parse_deepseek_error_response(response: Any) -> str:
    """
    Extrae un mensaje de error legible del cuerpo de una respuesta de error de DeepSeek.

    Args:
        response: Objeto requests.Response con status_code >= 400.

    Returns:
        Cadena con el código HTTP y el mensaje de la API (ej. "402 Payment Required: Insufficient Balance").
    """
    ok, _, err_msg = parse_deepseek_response(response)
    return err_msg or f"{getattr(response, 'status_code', '')} {getattr(response, 'reason', '')}"


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Cuenta el número de tokens en un texto usando tiktoken.
    
    Args:
        text: Texto a contar
        model: Modelo para determinar el encoding (default: gpt-3.5-turbo)
    
    Returns:
        Número de tokens en el texto
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        # Si el modelo no existe, usar cl100k_base (GPT-3.5/4)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


def clear_memory():
    """
    Libera memoria GPU y CPU después del procesamiento de un bloque.
    Optimizado para NVIDIA RTX 3050.
    """
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except ImportError:
        # torch no está instalado, no hay problema
        pass
    
    # Forzar garbage collection
    import gc
    gc.collect()


def validate_pdf(pdf_path: str) -> bool:
    """
    Valida que el archivo PDF existe y es legible.
    
    Args:
        pdf_path: Ruta al archivo PDF
    
    Returns:
        True si el PDF es válido, False en caso contrario
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si el archivo no es un PDF
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"El archivo PDF no existe: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError(f"El archivo no es un PDF: {pdf_path}")
    
    # Intentar abrir el PDF para verificar que es legible
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError(f"El PDF está vacío: {pdf_path}")
    except Exception as e:
        raise ValueError(f"El PDF no es legible: {e}")
    
    return True


def get_pdf_name(pdf_path: str) -> str:
    """
    Extrae el nombre del PDF sin extensión para usar en nombres de archivos.
    
    Args:
        pdf_path: Ruta al archivo PDF
    
    Returns:
        Nombre del PDF sin extensión
    """
    return os.path.splitext(os.path.basename(pdf_path))[0]


def ensure_directory(path: str):
    """
    Asegura que un directorio existe, creándolo si es necesario.
    
    Args:
        path: Ruta al directorio
    """
    os.makedirs(path, exist_ok=True)


def get_unique_output_dir(base_path: str, overwrite: bool = False) -> str:
    """
    Obtiene un directorio de salida único. Si el directorio ya existe y overwrite es False,
    agrega un sufijo numérico para evitar sobrescribir.
    
    Args:
        base_path: Ruta base del directorio deseado
        overwrite: Si True, permite sobrescribir el directorio existente
    
    Returns:
        Ruta al directorio (puede ser la original o una con sufijo numérico)
    """
    if overwrite:
        # Si se permite sobrescribir, usar la ruta original
        return base_path
    
    # Si el directorio no existe, usar la ruta original
    if not os.path.exists(base_path):
        return base_path
    
    # Si existe, buscar un nombre único agregando sufijo numérico
    base_dir = os.path.dirname(base_path) if os.path.dirname(base_path) else "."
    base_name = os.path.basename(base_path)
    
    counter = 1
    while True:
        new_name = f"{base_name}_{counter}"
        new_path = os.path.join(base_dir, new_name)
        
        if not os.path.exists(new_path):
            return new_path
        
        counter += 1
        
        # Límite de seguridad para evitar bucles infinitos
        if counter > 1000:
            raise RuntimeError(
                f"No se pudo encontrar un directorio único después de 1000 intentos. "
                f"Base: {base_path}"
            )
