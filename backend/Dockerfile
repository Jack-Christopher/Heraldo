FROM python:3.11-slim

WORKDIR /app

# Install system deps (Piper needs libsndfile, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy heraldo (core library) and backend
COPY heraldo /app/heraldo
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend /app/backend

WORKDIR /app/backend

RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', quiet=True)"

ENV PYTHONPATH=/app
ENV FLASK_APP=wsgi:app

EXPOSE 5001

CMD ["gunicorn", "-b", "0.0.0.0:5001", "-w", "2", "wsgi:app"]
