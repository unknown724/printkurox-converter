---
title: PrintKurox Cloud Converter
emoji: 🖨️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# PrintKurox Cloud DOCX Converter

High-fidelity document conversion microservice for PrintKurox Kiosk.
Converts `.docx`, `.doc`, `.rtf`, `.odt` to true vector PDFs using headless LibreOffice with metric-compatible typography.

### Endpoints
- `GET /health` - Healthcheck
- `POST /convert-docx?ext=docx` - Convert document payload (binary stream or multipart) to vector PDF
