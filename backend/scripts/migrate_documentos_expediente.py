"""
Crea la tabla de documentos de la operación.

Uso, desde la carpeta `backend/`:

    python scripts/migrate_documentos_expediente.py

Es idempotente: comprueba la tabla antes de crearla. A diferencia de
`migrate_risk_tables.py`, no invoca `init_db()`: solo crea
`documentos_expediente` y no reajusta ninguna fila existente.

**Por qué una tabla aparte de `documentos_cliente`.** El repositorio del cliente
guarda su expediente KYC: un archivo vigente por cada requisito del checklist,
con el nombre del requisito. Los documentos de una solicitud son otra cosa —
estados financieros del ejercicio, el avalúo de una garantía concreta, la
factura del bien a prendar—: pertenecen a la operación, no al padrón, son varios
por tipo y no responden a una lista cerrada. Mezclarlos obligaría a inventar
nombres de requisito para archivos que no lo son.

La conexión sale de `DATABASE_URL` en `backend/.env`.
"""

import sys
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_BACKEND))

from sqlalchemy import text  # noqa: E402

from database.db_core_sqlserver import engine  # noqa: E402

TABLA = "documentos_expediente"

CREAR = f"""CREATE TABLE {TABLA} (
    id INT IDENTITY(1,1) PRIMARY KEY,
    expediente_id INT NOT NULL,
    tipo_expediente NVARCHAR(20) NOT NULL,
    file_name NVARCHAR(255) NOT NULL,
    carpeta NVARCHAR(500) NOT NULL DEFAULT '',
    tamano_bytes BIGINT NOT NULL DEFAULT 0,
    cargado_por NVARCHAR(255) NOT NULL DEFAULT '',
    fecha_carga NVARCHAR(50) NOT NULL DEFAULT '',
    sp_sync_status NVARCHAR(50) NOT NULL DEFAULT 'No Sincronizado',
    fecha_sync NVARCHAR(50) NOT NULL DEFAULT '',
    eliminado BIT NOT NULL DEFAULT 0
)"""

# Columnas incrementales, para una tabla creada antes de que existiera la
# sincronizacion. Se declaran NOT NULL con DEFAULT: SQL Server deja en NULL las
# filas previas si la columna anadida admite nulos.
COLUMNAS = (
    ("sp_sync_status", "NVARCHAR(50) NOT NULL DEFAULT 'No Sincronizado'"),
    ("fecha_sync", "NVARCHAR(50) NOT NULL DEFAULT ''"),
)

INDICE = (f"CREATE INDEX ix_{TABLA}_expediente ON {TABLA} "
          "(tipo_expediente, expediente_id)")


def main() -> int:
    with engine.begin() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM sys.tables WHERE name = :t"), {"t": TABLA}
        ).fetchone() is not None

        if existe:
            print(f"{TABLA}: ya existía")
            for columna, tipo in COLUMNAS:
                hay = conn.execute(
                    text("SELECT 1 FROM sys.columns "
                         "WHERE object_id = OBJECT_ID(:t) AND name = :c"),
                    {"t": TABLA, "c": columna}).fetchone() is not None
                if hay:
                    print(f"  {columna}: ya existía, no se toca")
                else:
                    conn.execute(text(f"ALTER TABLE {TABLA} ADD {columna} {tipo}"))
                    print(f"  {columna}: creada")
        else:
            conn.execute(text(CREAR))
            # La lista de documentos se pide siempre por expediente.
            conn.execute(text(INDICE))
            print(f"{TABLA}: creada con su índice por expediente")

    with engine.connect() as conn:
        ok = conn.execute(
            text("SELECT 1 FROM sys.tables WHERE name = :t"), {"t": TABLA}
        ).fetchone() is not None

    if not ok:
        print(f"ERROR: la tabla {TABLA} sigue sin existir")
        return 1
    print(f"OK: {TABLA} disponible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
