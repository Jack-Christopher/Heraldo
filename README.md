# Heraldo - Sistema de Conversión PDF a Audiolibro

Sistema robusto en Python para procesar PDFs extensos (aprox. 80,000 palabras) y convertirlos en audiolibros educativos enriquecidos usando IA para parafrasear y añadir contexto.

## Características

- **Extracción inteligente de texto**: Limpia encabezados, pies de página y caracteres especiales
- **Procesamiento con IA**: Usa Ollama local para parafrasear y enriquecer el contenido
- **Sistema de checkpoints**: Reanuda el procesamiento desde donde se quedó
- **Múltiples motores TTS**: Soporta Piper TTS, Google TTS, y pyttsx3
- **Detección automática de capítulos**: Identifica capítulos o divide en bloques configurables
- **Optimizado para GPU**: Libera memoria después de cada bloque procesado

## Instalación

### 1. Dependencias Python

```bash
pip install -r requirements.txt
```

### 2. Descargar datos de NLTK

```bash
python -m nltk.downloader punkt
```

### 3. Instalar Ollama

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 4. Descargar modelo de Ollama

```bash
ollama pull llama3.1:8b
# O cualquier otro modelo disponible: qwen2.5:14b, mistral, etc.
```

### 5. Instalar Piper TTS (Opcional pero recomendado)

1. Descargar el ejecutable desde [Piper TTS Releases](https://github.com/rhasspy/piper/releases)
2. Descargar un modelo de voz (ej: `es_ES-davefx-medium`)
3. Configurar la ruta en el código o usar variable de entorno `PIPER_PATH`

Ejemplo de descarga de modelo:
```bash
# Ejemplo para español
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json
```

## Uso

### Uso básico

```bash
python -m heraldo.main --pdf ruta/al/documento.pdf
```

### Opciones completas

```bash
python -m heraldo.main \
    --pdf documento.pdf \
    --output /ruta/salida \
    --model llama3.1:8b \
    --tts-engine piper \
    --voice es_ES-davefx-medium \
    --block-size 2000 \
    --chapter-sentences 50 \
    --resume
```

### Parámetros

- `--pdf`: Ruta al archivo PDF (requerido)
- `--output`: Carpeta de salida (default: `outputs/{nombre_pdf}`)
- `--model`: Modelo de Ollama a usar (default: `llama3.1:8b`)
- `--tts-engine`: Motor TTS (`piper`, `gtts`, `pyttsx3`) (default: `piper`)
- `--voice`: Voz específica (depende del motor)
- `--resume`: Reanudar desde el último checkpoint
- `--block-size`: Tamaño de bloque en tokens (default: 2000)
- `--chapter-sentences`: Oraciones por capítulo si no se detectan (default: 50)

## Estructura de Salida

```
outputs/
└── nombre_del_pdf/
    ├── bloque_001.wav
    ├── bloque_002.wav
    ├── ...
    └── texto_procesado.txt  # Texto final consolidado
```

## Sistema de Checkpoints

El sistema guarda automáticamente el progreso en `checkpoints/{pdf_name}_checkpoint.json`. Si el proceso se interrumpe, puedes reanudarlo con la opción `--resume`.

## Motores TTS

### Piper TTS (Recomendado)
- Ultra rápido y local
- Requiere descargar ejecutable y modelo
- Configurar ruta con variable de entorno `PIPER_PATH` o en código

### Google TTS (gTTS)
- Requiere conexión a internet
- Buena calidad de voz
- No requiere configuración adicional

### pyttsx3
- Offline y multiplataforma
- Voz sintética básica
- No requiere configuración adicional

## Requisitos del Sistema

- Python 3.8+
- NVIDIA RTX 3050 o superior (recomendado para procesamiento rápido)
- Al menos 8GB RAM
- Ollama instalado y ejecutándose localmente

## Notas

- El procesamiento de PDFs grandes puede tardar varias horas
- Se recomienda usar checkpoints para documentos extensos
- El sistema optimiza automáticamente el uso de memoria GPU
