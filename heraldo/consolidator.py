"""
Módulo para consolidar y reorganizar bloques de texto procesados.
Fase 3 del sistema Heraldo.
"""

import re
from typing import List, Tuple, Optional
import nltk

# Descargar datos de NLTK si no están disponibles
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception:
        pass


class TextConsolidator:
    """
    Consolida bloques de texto procesados y los reorganiza en capítulos o bloques lógicos.
    """
    
    # Patrones para detectar capítulos
    CHAPTER_PATTERNS = [
        r'^capítulo\s+[ivxlcdm]+',  # Capítulo I, II, III, etc.
        r'^capítulo\s+\d+',  # Capítulo 1, 2, 3, etc.
        r'^chapter\s+[ivxlcdm]+',  # Chapter I, II, III, etc.
        r'^chapter\s+\d+',  # Chapter 1, 2, 3, etc.
        r'^[ivxlcdm]+\.',  # I., II., III., etc.
        r'^parte\s+[ivxlcdm]+',  # Parte I, II, III, etc.
        r'^parte\s+\d+',  # Parte 1, 2, 3, etc.
        r'^part\s+[ivxlcdm]+',  # Part I, II, III, etc.
        r'^part\s+\d+',  # Part 1, 2, 3, etc.
    ]
    
    def __init__(self, chapter_words: int = 100):
        """
        Inicializa el consolidador de texto.
        
        Args:
            chapter_words: Número de palabras por bloque/capítulo
        """
        self.chapter_words = chapter_words
    
    def consolidate_blocks(self, blocks: List[str]) -> str:
        """
        Une todos los bloques de texto en un texto continuo.
        Intenta unir fragmentos que puedan haber sido cortados arbitrariamente.
        
        Args:
            blocks: Lista de bloques de texto procesados
        
        Returns:
            Texto consolidado
        """
        if not blocks:
            return ""
        
        consolidated = []
        
        for i, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue
            
            # Si el bloque anterior no termina con puntuación y el actual no empieza con mayúscula,
            # probablemente fueron cortados arbitrariamente
            if i > 0 and consolidated:
                prev_block = consolidated[-1]
                
                # Si el bloque anterior no termina con puntuación de fin de oración
                if not re.search(r'[.!?]\s*$', prev_block):
                    # Y el bloque actual no empieza con mayúscula (excepto si es un nombre propio)
                    if block and not block[0].isupper():
                        # Unir sin espacio adicional
                        consolidated[-1] = prev_block + " " + block
                        continue
            
            consolidated.append(block)
        
        return "\n\n".join(consolidated)
    
    def detect_chapters(self, text: str) -> List[Tuple[int, str]]:
        """
        Detecta capítulos en el texto usando patrones comunes.
        
        Args:
            text: Texto completo a analizar
        
        Returns:
            Lista de tuplas (índice_inicio, título_capítulo) o lista vacía si no se detectan
        """
        chapters = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Probar cada patrón
            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    chapters.append((i, line_stripped))
                    break
        
        return chapters
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Divide el texto en oraciones usando NLTK.
        
        Args:
            text: Texto a dividir
        
        Returns:
            Lista de oraciones
        """
        try:
            sentences = nltk.sent_tokenize(text)
            # Filtrar oraciones vacías o muy cortas
            return [s.strip() for s in sentences if len(s.strip()) > 10]
        except Exception:
            # Fallback: división simple por puntuación
            sentences = re.split(r'[.!?]+\s+', text)
            return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def split_into_words(self, text: str) -> List[str]:
        """
        Divide el texto en palabras.
        
        Args:
            text: Texto a dividir
        
        Returns:
            Lista de palabras
        """
        # Dividir por espacios y filtrar palabras vacías
        words = re.findall(r'\S+', text)
        return [w for w in words if w.strip()]
    
    def split_text_by_words(self, text: str, words_per_chunk: int) -> List[str]:
        """
        Divide el texto en bloques de N palabras.
        
        Args:
            text: Texto a dividir
            words_per_chunk: Número de palabras por bloque
        
        Returns:
            Lista de bloques de texto
        """
        words = self.split_into_words(text)
        chunks = []
        
        for i in range(0, len(words), words_per_chunk):
            chunk_words = words[i:i + words_per_chunk]
            chunk_text = ' '.join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        return chunks if chunks else [text]
    
    def split_into_chapters(
        self, 
        text: str, 
        detected_chapters: Optional[List[Tuple[int, str]]] = None
    ) -> List[str]:
        """
        Divide el texto en bloques de N palabras.
        Si se detectan capítulos, primero extrae cada capítulo y luego divide cada uno en bloques de palabras.
        Si no, divide todo el texto en bloques de N palabras.
        
        Args:
            text: Texto consolidado a dividir
            detected_chapters: Lista de capítulos detectados (índice, título)
        
        Returns:
            Lista de bloques de texto (cada uno con aproximadamente chapter_words palabras)
        """
        all_blocks = []
        
        if detected_chapters and len(detected_chapters) > 0:
            # Si hay capítulos detectados, extraer cada capítulo y dividirlo en bloques de palabras
            lines = text.split('\n')
            
            for i, (chapter_idx, chapter_title) in enumerate(detected_chapters):
                start_idx = chapter_idx
                end_idx = detected_chapters[i + 1][0] if i + 1 < len(detected_chapters) else len(lines)
                
                chapter_text = '\n'.join(lines[start_idx:end_idx]).strip()
                if chapter_text:
                    # Dividir este capítulo en bloques de palabras
                    chapter_blocks = self.split_text_by_words(chapter_text, self.chapter_words)
                    all_blocks.extend(chapter_blocks)
        else:
            # No hay capítulos detectados, dividir todo el texto en bloques de palabras
            all_blocks = self.split_text_by_words(text, self.chapter_words)
        
        return all_blocks if all_blocks else [text]
    
    def process(
        self, 
        processed_blocks: List[str]
    ) -> Tuple[List[str], bool]:
        """
        Proceso completo de consolidación y división en capítulos.
        
        Args:
            processed_blocks: Lista de bloques procesados por la IA
        
        Returns:
            Tupla (lista_de_capítulos, capítulos_detectados)
            donde capítulos_detectados es True si se detectaron capítulos automáticamente
        """
        print("Consolidando bloques de texto...")
        consolidated_text = self.consolidate_blocks(processed_blocks)
        
        print("Detectando capítulos...")
        detected_chapters = self.detect_chapters(consolidated_text)
        chapters_detected = len(detected_chapters) > 0
        
        if chapters_detected:
            print(f"Se detectaron {len(detected_chapters)} capítulos")
            print(f"Dividiendo cada capítulo en bloques de {self.chapter_words} palabras...")
        else:
            print(f"No se detectaron capítulos. Dividiendo en bloques de {self.chapter_words} palabras...")
        
        chapters = self.split_into_chapters(consolidated_text, detected_chapters)
        print(f"Texto dividido en {len(chapters)} bloques finales (cada uno con ~{self.chapter_words} palabras)")
        
        return chapters, chapters_detected
