# Heraldo Web - Guía de despliegue

## Requisitos

- Docker y Docker Compose
- Para producción: JWT_SECRET en entorno

## Puertos

| Servicio   | Puerto | Uso                                      |
|-----------|--------|------------------------------------------|
| Frontend  | 3001   | App React (nginx)                        |
| API       | 5001   | Flask backend                            |
| MongoDB   | 27018  | Base de datos (mapeo host)               |

## Despliegue con Docker

```bash
# Crear .env desde plantilla
cp .env.docker .env
# Editar .env y poner JWT_SECRET seguro

# Levantar servicios
docker compose up -d

# Ver logs
docker compose logs -f api
```

Acceso: http://localhost:3001

## Desarrollo local

### Backend

```bash
# Crear venv e instalar dependencias
cd backend && pip install -r requirements.txt
cd ..

# MongoDB (Docker)
docker run -d -p 27018:27017 --name heraldo-mongo mongo:7

# Variables
export MONGODB_URI=mongodb://localhost:27018/heraldo
export JWT_SECRET=dev-secret
export OUTPUTS_DIR=./outputs
export UPLOADS_DIR=./uploads

# Ejecutar API
cd backend && python -m flask run --port 5001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend en http://localhost:3001 (proxy a API en 5001)

## TTS

Por defecto usa **gTTS** (requiere internet). Para usar Piper en Docker, monta el binario y modelos y configura `TTS_ENGINE=piper`.
