import pandas as pd
from sqlalchemy import text
from database.db_core_sqlserver import get_connection

engine = get_connection()
with engine.connect() as conn:
    res = conn.execute(text("SELECT TOP 5 id, fecha, cliente FROM expedientes_wf ORDER BY id DESC")).fetchall()
    print("ORDER BY id DESC:", res)

    res2 = conn.execute(text("SELECT TOP 5 id, fecha, cliente FROM expedientes_wf ORDER BY id ASC")).fetchall()
    print("ORDER BY id ASC:", res2)
