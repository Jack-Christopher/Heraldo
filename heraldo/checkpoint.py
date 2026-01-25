"""
Sistema de checkpoints para guardar y reanudar el progreso del procesamiento.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from .utils import get_pdf_name, ensure_directory


class CheckpointManager:
    """
    Gestiona el guardado y carga de checkpoints para reanudar el procesamiento.
    """
    
    def __init__(self, pdf_path: str, checkpoint_dir: str = "checkpoints"):
        """
        Inicializa el gestor de checkpoints.
        
        Args:
            pdf_path: Ruta al archivo PDF
            checkpoint_dir: Directorio donde guardar checkpoints
        """
        self.pdf_path = pdf_path
        self.pdf_name = get_pdf_name(pdf_path)
        self.checkpoint_dir = checkpoint_dir
        ensure_directory(checkpoint_dir)
        self.checkpoint_file = os.path.join(
            checkpoint_dir, 
            f"{self.pdf_name}_checkpoint.json"
        )
    
    def save_checkpoint(
        self, 
        last_block: int, 
        processed_blocks: List[str],
        total_blocks: int
    ):
        """
        Guarda el estado actual del procesamiento.
        
        Args:
            last_block: Índice del último bloque procesado exitosamente
            processed_blocks: Lista de bloques procesados (texto enriquecido)
            total_blocks: Número total de bloques a procesar
        """
        checkpoint_data = {
            "pdf_path": self.pdf_path,
            "pdf_name": self.pdf_name,
            "last_block": last_block,
            "processed_blocks": processed_blocks,
            "total_blocks": total_blocks,
            "timestamp": datetime.now().isoformat(),
            "progress_percent": (last_block + 1) / total_blocks * 100 if total_blocks > 0 else 0
        }
        
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Advertencia: No se pudo guardar el checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """
        Carga el checkpoint más reciente si existe.
        
        Returns:
            Diccionario con los datos del checkpoint o None si no existe
        """
        if not os.path.exists(self.checkpoint_file):
            return None
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # Validar que el checkpoint corresponde al mismo PDF
            if checkpoint_data.get("pdf_path") != self.pdf_path:
                print("Advertencia: El checkpoint corresponde a un PDF diferente")
                return None
            
            return checkpoint_data
        except Exception as e:
            print(f"Advertencia: No se pudo cargar el checkpoint: {e}")
            return None
    
    def should_resume(self) -> bool:
        """
        Verifica si existe un checkpoint válido para reanudar.
        
        Returns:
            True si se puede reanudar, False en caso contrario
        """
        checkpoint = self.load_checkpoint()
        if checkpoint is None:
            return False
        
        # Verificar que el checkpoint tiene datos válidos
        if "processed_blocks" not in checkpoint or "last_block" not in checkpoint:
            return False
        
        # Verificar que no está completo
        last_block = checkpoint.get("last_block", -1)
        total_blocks = checkpoint.get("total_blocks", 0)
        
        return last_block < total_blocks - 1
    
    def get_resume_data(self) -> Optional[Dict]:
        """
        Obtiene los datos necesarios para reanudar el procesamiento.
        
        Returns:
            Diccionario con last_block y processed_blocks, o None
        """
        checkpoint = self.load_checkpoint()
        if checkpoint is None:
            return None
        
        return {
            "last_block": checkpoint.get("last_block", -1),
            "processed_blocks": checkpoint.get("processed_blocks", []),
            "total_blocks": checkpoint.get("total_blocks", 0)
        }
    
    def clear_checkpoint(self):
        """
        Elimina el checkpoint (útil cuando el procesamiento se completa).
        """
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
            except Exception as e:
                print(f"Advertencia: No se pudo eliminar el checkpoint: {e}")
