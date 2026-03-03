# Verificación de email y costos

## Configuración

Para enviar correos de verificación, configura en `.env`:

```
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=tu_usuario
MAIL_PASSWORD=tu_contraseña
MAIL_FROM=noreply@tudominio.com
FRONTEND_URL=https://tudominio.com
```

## Costos

### En local (desarrollo)

- **Sin SMTP configurado**: El enlace de verificación se loguea en consola. No hay costo.
- **Con SMTP local** (sendmail, Postfix): Sin costo adicional, pero los correos suelen ir a spam.

### En VPS

- **Postfix/SMTP propio**: No hay costo extra. Riesgo alto de ir a spam si el servidor no tiene SPF/DKIM/DMARC bien configurados.
- **Servicios transaccionales** (SendGrid, Mailgun, Amazon SES):
  - SendGrid: ~100 emails/día gratis, luego ~\$15/mes
  - Mailgun: ~5000 emails/mes gratis los primeros 3 meses
  - Amazon SES: ~62.000 emails/mes gratis si envías desde EC2

**Recomendación**: Para producción, usa un servicio transaccional con tier gratuito o económico.
