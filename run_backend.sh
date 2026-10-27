#!/bin/bash
# Levanta la API FastAPI en modo desarrollo, con recarga automática.
#
# El puerto es el 8000 porque es al que apunta BACKEND_ORIGIN en
# frontend/.env.local: el navegador nunca habla con este servicio directamente,
# sino que el servidor de Next le reenvía /api, /health y /token.
#
# Se invoca como `python -m uvicorn` y no con el ejecutable `uvicorn` a secas:
# así arranca siempre con el intérprete activo —el del entorno virtual, si está
# activado— en lugar de depender del envoltorio que pip deja en el PATH.
set -e

cd "$(dirname "$0")/backend"

# /token firma los JWT con esta clave y falla cerrado si no está configurada.
if [ -z "$JWT_SECRET_KEY" ] && ! grep -q "^JWT_SECRET_KEY=" .env 2>/dev/null; then
  echo "AVISO: falta JWT_SECRET_KEY (mínimo 32 caracteres) en el entorno o en"
  echo "       backend/.env. El servicio arranca, pero el inicio de sesión fallará."
fi

exec python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
