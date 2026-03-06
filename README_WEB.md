# Heraldo Web - Guía de despliegue

## Requisitos

- Docker y Docker Compose
- Para producción: JWT_SECRET y MONGO_ROOT_PASSWORD en entorno

## Puertos

| Servicio   | Puerto | Uso                                      |
|-----------|--------|------------------------------------------|
| Frontend  | 3001   | App React (nginx)                        |
| API       | 5001   | Flask backend                            |
| MongoDB   | —      | No expuesto (solo red interna Docker)    |

## Despliegue con Docker

```bash
# Crear .env desde plantilla
cp .env.example .env
# Editar .env: JWT_SECRET, MONGO_ROOT_PASSWORD (autenticación MongoDB)

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

# MongoDB (Docker con auth)
docker run -d -p 27018:27017 --name heraldo-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=heraldo_admin \
  -e MONGO_INITDB_ROOT_PASSWORD=devpassword \
  mongo:7

# Variables (usar mismo usuario/contraseña que el contenedor)
export MONGODB_URI=mongodb://heraldo_admin:devpassword@localhost:27018/heraldo?authSource=admin
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

## Roles y administración

Para tener un usuario administrador, configura `ADMIN_EMAILS` en `.env` (emails separados por coma). Al iniciar la API, la migración 005 promoverá esos usuarios a rol `admin`. Los admins pueden:

- Ver y gestionar todos los usuarios
- Editar límites por usuario (max PDFs, max palabras/PDF)
- Ver los PDFs y audios de cualquier usuario

## TTS

Por defecto usa **gTTS** (requiere internet). Para usar Piper en Docker, monta el binario y modelos y configura `TTS_ENGINE=piper`.
