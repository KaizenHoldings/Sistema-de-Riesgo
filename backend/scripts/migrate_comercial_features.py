"""
Añade a los expedientes la columna que enlaza una reevaluación con su origen.

Uso, desde la carpeta `backend/`:

    python scripts/migrate_comercial_features.py

Es idempotente: comprueba la columna antes de crearla, así que volver a
ejecutarlo no altera nada. A diferencia de `migrate_risk_tables.py`, no invoca
`init_db()`: solo toca `expedientes_wf` y `expedientes_auto`, y no reajusta
ninguna fila existente.

`parent_expediente_id` admite nulos porque un expediente nacido de una solicitud
nueva no procede de ninguno; solo lo rellena la reevaluación, con el id del
expediente rechazado o devuelto del que se clonó.

La conexión sale de `DATABASE_URL` en `backend/.env`.
"""

import sys
from pathlib import Path

# El script vive en backend/scripts/, pero importa los paquetes de backend/.
RAIZ_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_BACKEND))

from sqlalchemy import text  # noqa: E402

from database.db_core_sqlserver import engine  # noqa: E402

TABLAS = ("expedientes_wf", "expedientes_auto")
COLUMNA = "parent_expediente_id"


def main() -> int:
    with engine.begin() as conn:
        def existe_tabla(nombre: str) -> bool:
            return conn.execute(text("SELECT 1 FROM sys.tables WHERE name = :t"),
                                {"t": nombre}).fetchone() is not None

        def existe_columna(tabla: str, columna: str) -> bool:
            return conn.execute(
                text("SELECT 1 FROM sys.columns "
                     "WHERE object_id = OBJECT_ID(:t) AND name = :c"),
                {"t": tabla, "c": columna}).fetchone() is not None

        for tabla in TABLAS:
            if not existe_tabla(tabla):
                print(f"ERROR: no existe la tabla {tabla}.")
                return 1
            if existe_columna(tabla, COLUMNA):
                print(f"{tabla}.{COLUMNA}: ya existía, no se toca")
                continue
            # El nombre de tabla es una constante del módulo, nunca un dato de
            # entrada: por eso puede componerse en la sentencia.
            conn.execute(text(f"ALTER TABLE {tabla} ADD {COLUMNA} INT NULL"))
            print(f"{tabla}.{COLUMNA}: creada")

    with engine.connect() as conn:
        faltan = [
            tabla for tabla in TABLAS
            if conn.execute(
                text("SELECT 1 FROM sys.columns "
                     "WHERE object_id = OBJECT_ID(:t) AND name = :c"),
                {"t": tabla, "c": COLUMNA}).fetchone() is None
        ]

    if faltan:
        print(f"ERROR: la columna sigue sin existir en: {', '.join(faltan)}")
        return 1
    print(f"OK: {COLUMNA} disponible en {', '.join(TABLAS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
