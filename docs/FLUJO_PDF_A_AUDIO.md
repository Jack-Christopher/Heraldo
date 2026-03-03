# Flujo: PDF → Audiolibro

## Diagrama de flujo

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 1. SUBIR PDF                                                                        │
│    Usuario → UploadPdf → Arrastra/selecciona PDF (solo .pdf) → "Convertir"          │
│    POST /api/pdf/upload (multipart/form-data)                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 2. VALIDACIÓN Y COLA                                                                │
│    Backend valida: cuota, extensión PDF, límites (páginas/palabras)                 │
│    Guarda PDF en uploads/{user_id}/{doc_id}.pdf                                     │
│    Crea documento en MongoDB (status: pending)                                      │
│    Encola en worker → Redirige a /my-pdfs                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 3. PROCESAMIENTO (worker en segundo plano)                                          │
│    Extrae texto → (opcional) procesa con IA → TTS → WAV                             │
│    output_path = outputs/{user_id}/{doc_id}/{nombre}.wav                            │
│    Actualiza documento: status=completed, output_path                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 4. REPRODUCIR O DESCARGAR                                                           │
│    ┌─────────────────────────────────────────────────────────────────────────────┐  │
│    │ REPRODUCIR (streaming, sin descargar todo):                                 │  │
│    │   GET /api/pdf/{id}/stream → Range support → <audio src="...">              │  │
│    │   Posición (min:seg) se guarda en localStorage por doc_id                   │  │
│    └─────────────────────────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────────────────────────┐  │
│    │ DESCARGAR (opcional):                                                       │  │
│    │   GET /api/pdf/{id}/download → as_attachment=True → blob → URL.revokeObject │  │
│    │   ⚠️ Archivos pueden pesar decenas/centenas de MB                           │  │
│    └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Detalle por pasos

| Paso | Qué ocurre |
|------|------------|
| **1. Subir** | Drag & drop o clic; solo PDFs; validación cliente (MIME) y servidor (extensión + límites). |
| **2. Validación** | Cuota de PDFs activos (max por usuario), páginas máx, palabras máx. Si falla → error sin guardar. |
| **3. Procesamiento** | Worker procesa en background. Frontend hace polling cada 3s en /my-pdfs. |
| **4. Audio** | **Reproducir**: streaming, no se descarga todo; posición guardada en localStorage. **Descargar**: opción explícita para guardar WAV localmente. |
