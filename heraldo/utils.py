"""
Utilidades generales para el sistema Heraldo.
Incluye funciones para conteo de tokens, limpieza de memoria, validación y barras de progreso.
"""

import os
import tiktoken
from typing import Optional


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
