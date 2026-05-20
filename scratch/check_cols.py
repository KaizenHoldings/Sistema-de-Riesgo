import pandas as pd
from sqlalchemy import text
from database.db_core_sqlserver import get_connection

engine = get_connection()
with engine.connect() as conn:
    res_wf = conn.execute(text("SELECT TOP 1 * FROM expedientes_wf")).fetchone()
    print("Columns expedientes_wf:", res_wf._mapping.keys() if res_wf else "No rows")
    
    res_auto = conn.execute(text("SELECT TOP 1 * FROM expedientes_auto")).fetchone()
    print("Columns expedientes_auto:", res_auto._mapping.keys() if res_auto else "No rows")
