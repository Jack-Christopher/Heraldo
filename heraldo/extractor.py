"""
Módulo para extracción y limpieza de texto de archivos PDF.
Fase 1 del sistema Heraldo.
"""

import re
import pdfplumber
from typing import List, Optional
from .utils import count_tokens, get_pdf_name


class PDFExtractor:
    """
    Clase para extraer y limpiar texto de archivos PDF.
    """
    
    def __init__(self, pdf_path: str, block_size: int = 2000):
        """
        Inicializa el extractor de PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
            block_size: Tamaño de bloque en tokens (default: 2000)
        """
        self.pdf_path = pdf_path
        self.block_size = block_size
        self.pdf_name = get_pdf_name(pdf_path)
    
    def extract_text(self) -> str:
        """
        Extrae el texto crudo del PDF.
        
        Returns:
            Texto completo del PDF como string
        """
        text_parts = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    print(f"Advertencia: Error al extraer texto de la página {page_num}: {e}")
                    continue
        
        return "\n".join(text_parts)
    
    def clean_text(self, text: str) -> str:
        """
        Limpia el texto eliminando encabezados, pies de página, números de página
        y caracteres especiales que ensucian la lectura.
        
        Preserva pies de página si contienen información relevante (contexto).
        
        Args:
            text: Texto crudo a limpiar
        
        Returns:
            Texto limpio
        """
        # Eliminar números de página solos (líneas con solo números)
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
        
        # Eliminar encabezados repetitivos (líneas que se repiten en cada página)
        # Esto es una heurística simple - se puede mejorar
        lines = text.split('\n')
        seen_headers = {}
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            # Si la línea es muy corta y se repite mucho, probablemente es encabezado
            if len(line_stripped) < 50:
                count = seen_headers.get(line_stripped, 0)
                seen_headers[line_stripped] = count + 1
                # Si aparece más de 3 veces, probablemente es encabezado
                if count > 3:
                    continue
            
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Eliminar múltiples espacios en blanco
        text = re.sub(r' +', ' ', text)
        
        # Eliminar múltiples saltos de línea
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Limpiar caracteres especiales problemáticos pero mantener puntuación
        # Eliminar caracteres de control excepto saltos de línea y tabs
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalizar comillas y guiones
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('—', '-').replace('–', '-')
        
        return text.strip()
    
    def split_into_blocks(self, text: str) -> List[str]:
        """
        Divide el texto en bloques lógicos de aproximadamente block_size tokens.
        Intenta mantener párrafos completos.
        
        Args:
            text: Texto a dividir
        
        Returns:
            Lista de bloques de texto
        """
        blocks = []
        paragraphs = text.split('\n\n')
        
        current_block = []
        current_tokens = 0
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            para_tokens = count_tokens(paragraph)
            
            # Si un párrafo solo es más grande que el tamaño del bloque,
            # dividirlo por oraciones
            if para_tokens > self.block_size:
                # Guardar bloque actual si existe
                if current_block:
                    blocks.append('\n\n'.join(current_block))
                    current_block = []
                    current_tokens = 0
                
                # Dividir párrafo grande por oraciones
                sentences = re.split(r'[.!?]+\s+', paragraph)
                for sentence in sentences:
                    if not sentence.strip():
                        continue
                    
                    sent_tokens = count_tokens(sentence)
                    
                    if current_tokens + sent_tokens > self.block_size and current_block:
                        blocks.append('\n\n'.join(current_block))
                        current_block = []
                        current_tokens = 0
                    
                    current_block.append(sentence)
                    current_tokens += sent_tokens
            else:
                # Si agregar este párrafo excede el tamaño, guardar bloque actual
                if current_tokens + para_tokens > self.block_size and current_block:
                    blocks.append('\n\n'.join(current_block))
                    current_block = []
                    current_tokens = 0
                
                current_block.append(paragraph)
                current_tokens += para_tokens
        
        # Agregar el último bloque si existe
        if current_block:
            blocks.append('\n\n'.join(current_block))
        
        return blocks
    
    def process(self, clean: bool = True) -> List[str]:
        """
        Proceso completo: extrae, opcionalmente limpia y divide el texto en bloques.
        
        Args:
            clean: Si True, limpia el texto. Si False, usa el texto crudo.
        
        Returns:
            Lista de bloques de texto listos para procesamiento
        """
        print("Extrayendo texto del PDF...")
        raw_text = self.extract_text()
        
        if clean:
            print("Limpiando texto...")
            processed_text = self.clean_text(raw_text)
        else:
            print("Usando texto crudo (sin limpieza)...")
            processed_text = raw_text
        
        print(f"Dividiendo texto en bloques de ~{self.block_size} tokens...")
        blocks = self.split_into_blocks(processed_text)
        
        print(f"Texto dividido en {len(blocks)} bloques")
        return blocks
    
    def extract_raw_text(self) -> str:
        """
        Extrae el texto crudo del PDF sin procesamiento adicional.
        Útil para guardar el texto original.
        
        Returns:
            Texto crudo del PDF
        """
        return self.extract_text()