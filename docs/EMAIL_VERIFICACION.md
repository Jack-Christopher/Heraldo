# Verificación de email y costos

## Configuración (Brevo SMTP)

Configura en `.env` (docker-compose pasa estas variables al contenedor API):

```
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USERNAME=xxx@smtp-brevo.com
MAIL_PASSWORD=tu-clave-smtp
MAIL_FROM=noreply@tudominio.com
FRONTEND_URL=http://tu-ip-o-dominio:3001
```

**Importante**: `FRONTEND_URL` debe ser la URL pública donde los usuarios acceden al frontend.

### Brevo SMTP

1. Brevo → **Transactional** → **SMTP y API**
2. **MAIL_USERNAME** = "Iniciar sesión" (ej: `a3dbd9001@smtp-brevo.com`)
3. **MAIL_PASSWORD** = Valor de la clave SMTP (crea una en "Tus claves SMTP")
4. **MAIL_FROM** = Email verificado como remitente (Senders) - el que verán los destinatarios

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
