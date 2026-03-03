# Seguridad de MongoDB

## Cambios implementados

1. **Sin puerto expuesto**: MongoDB ya no está mapeado al host (antes 27018). Solo es accesible desde la red interna Docker.
2. **Autenticación obligatoria**: Se usa `MONGO_INITDB_ROOT_USERNAME` y `MONGO_INITDB_ROOT_PASSWORD`.

## Configuración

En `.env`:
```
MONGO_ROOT_USER=heraldo_admin
MONGO_ROOT_PASSWORD=contraseña-segura
```

## Volumen existente (reinstalación) — OBLIGATORIO si MongoDB falla

Si MongoDB arrancó antes **sin autenticación**, el volumen ya tiene datos y el init se salta. No se crea el usuario. El healthcheck fallará. **Debes borrar el volumen**:

```bash
docker compose down
docker volume ls | grep mongo          # ver nombre exacto (p. ej. heraldo_mongodb_data)
docker volume rm heraldo_mongodb_data  # usa el nombre que salga
docker compose up -d
```

**Advertencia**: Borra todos los datos de MongoDB.
