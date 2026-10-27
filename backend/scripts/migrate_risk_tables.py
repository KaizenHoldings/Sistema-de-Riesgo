"""
Despliega en SQL Server las tablas de evaluaciones de Riesgo.

Uso, desde la carpeta `backend/`:

    python scripts/migrate_risk_tables.py

Ejecuta `init_db()` completo, que es idempotente: crea solo las tablas y
columnas que falten. Además de `evaluaciones_riesgo_corp` y
`evaluaciones_riesgo_auto`, aplica todo lo que `init_db()` hace en cada
arranque: las columnas incrementales, la realineación de `estado_workflow`
con el dictamen y el alta del Superadmin por omisión si no existe. Conviene
revisarlo antes de lanzarlo contra una base de producción.

La conexión sale de `DATABASE_URL` en `backend/.env`.
"""

import sys
from pathlib import Path

# El script vive en backend/scripts/, pero importa los paquetes de backend/.
RAIZ_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_BACKEND))

from sqlalchemy import text  # noqa: E402

from database.db_core_sqlserver import engine, init_db  # noqa: E402

TABLAS = ("evaluaciones_riesgo_corp", "evaluaciones_riesgo_auto")


def main() -> int:
    init_db()

    with engine.connect() as conn:
        faltan = [
            tabla for tabla in TABLAS
            if conn.execute(text("SELECT 1 FROM sys.tables WHERE name = :t"),
                            {"t": tabla}).fetchone() is None
        ]

    if faltan:
        print(f"ERROR: init_db() terminó pero no existen: {', '.join(faltan)}")
        return 1
    print(f"OK: tablas disponibles: {', '.join(TABLAS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
