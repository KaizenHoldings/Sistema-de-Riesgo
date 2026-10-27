#!/bin/bash
# Levanta la interfaz Next.js en modo desarrollo, en http://localhost:3000.
#
# Necesita el backend en marcha: las peticiones a /api se reenvían a él.
set -e

cd "$(dirname "$0")/frontend"

exec npm run dev
