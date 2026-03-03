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

## Volumen existente (reinstalación)

Si tienes un volumen de MongoDB anterior (por ejemplo, después de un incidente o migración), **debes eliminarlo** para que se ejecute el init que crea el usuario con contraseña:

```bash
docker compose down
docker volume rm heraldo_mongodb_data   # o el nombre que muestre: docker volume ls
# Añadir MONGO_ROOT_PASSWORD a .env
docker compose up -d
```

**Advertencia**: Esto borra todos los datos de MongoDB. Haz backup si necesitas conservar algo.
