"""
Invoke Heraldo pipeline for PDF processing.
Uses TTS_ENGINE env (default: piper). Set to gtts if Piper not available in Docker.
"""
import os
import sys

# Ensure heraldo is importable
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # Heraldo/
sys.path.insert(0, ROOT)


def run_pipeline(pdf_path: str, output_dir: str):
    """
    Run HeraldoPipeline on a PDF.

    Args:
        pdf_path: Path to the uploaded PDF
        output_dir: Directory for outputs (text, blocks, merged audio)

    Returns:
        (success, error_message)
        If success: output_dir contains the merged WAV (named like the PDF).
        If not: error_message describes the failure.
    """
    try:
        from heraldo.main import HeraldoPipeline

        tts_engine = os.environ.get("TTS_ENGINE", "piper")
        pipeline = HeraldoPipeline(
            pdf_path=pdf_path,
            output_dir=output_dir,
            use_ai=False,
            clean_pdf=True,
            tts_engine_name=tts_engine,
            merge_audio=True,
            overwrite=True,
        )
        pipeline.run()
        return True, None
    except Exception as e:
        return False, str(e)
