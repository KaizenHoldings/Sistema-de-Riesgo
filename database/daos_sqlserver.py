import pandas as pd
import streamlit as st
from sqlalchemy import text
from .db_core_sqlserver import get_connection, db_action
from .models import Usuario
from services.security_service import SecurityService

def _build_where(filters: dict, _table: str = "") -> tuple:
    """
    Construye dinámicamente una cláusula WHERE y su lista de parámetros
    usando nombres para SQLAlchemy.
    """
    clauses = []
    params = {}
    for i, (col, val) in enumerate(filters.items()):
        if val is not None:
            param_name = f"p{i}"
            clauses.append(f"{col} = :{param_name}")
            params[param_name] = val
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params

class UsuarioDAO:
    @staticmethod
    def get_by_credentials(user, password):
        engine = get_connection()
        with engine.connect() as conn:
            query = text("SELECT * FROM usuarios WHERE [user] = :u")
            row = conn.execute(query, {"u": user}).fetchone()
            
            if row:
                stored_hash = row[1]
                if SecurityService.verify_password(password, stored_hash):
                    return Usuario(user=row[0], password=stored_hash, role=row[2])
        return None

    @staticmethod
    def upsert(user, password, role):
        hashed_password = SecurityService.hash_password(password)
        query = """
        MERGE usuarios AS target
        USING (SELECT :u AS [user], :p AS [password], :r AS [role]) AS source
        ON (target.[user] = source.[user])
        WHEN MATCHED THEN
            UPDATE SET [password] = source.[password], [role] = source.[role]
        WHEN NOT MATCHED THEN
            INSERT ([user], [password], [role]) VALUES (source.[user], source.[password], source.[role]);
        """
        db_action(query, {"u": user, "p": hashed_password, "r": role})

    @staticmethod
    def update_password(user, new_password):
        hashed_password = SecurityService.hash_password(new_password)
        db_action("UPDATE usuarios SET [password] = :p WHERE [user] = :u", {"p": hashed_password, "u": user})

    @staticmethod
    def get_all_as_df():
        engine = get_connection()
        return pd.read_sql_query(text("SELECT [user] AS Usuario, [role] AS Rol FROM usuarios"), engine)

class ConfigParametroDAO:
    @staticmethod
    @st.cache_data
    def get_all_as_dict():
        engine = get_connection()
        df = pd.read_sql_query(text("SELECT * FROM config_parametros"), engine)
        return dict(zip(df['clave'], df['valor']))

    @staticmethod
    def update_param(clave, valor):
        db_action("UPDATE config_parametros SET valor = :v WHERE clave = :k", {"v": valor, "k": clave})

class ExpedienteCorporativoDAO:
    @staticmethod
    def create(fecha, cliente, rif, monto):
        db_action("INSERT INTO expedientes_wf (fecha, cliente, rif, monto) VALUES (:f, :c, :r, :m)",
                  {"f": fecha, "c": cliente, "r": rif, "m": monto})

    @staticmethod
    def get_all_as_df():
        engine = get_connection()
        return pd.read_sql_query(text("SELECT * FROM expedientes_wf"), engine)

    @staticmethod
    def count(dictamen: str = None, cliente: str = None) -> int:
        engine = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_wf')
        with engine.connect() as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM expedientes_wf{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      dictamen: str = None, cliente: str = None) -> pd.DataFrame:
        engine = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_wf')
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM expedientes_wf{where} ORDER BY id DESC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        return pd.read_sql_query(text(query), engine, params=params)
    
    @staticmethod
    def delete(exp_id):
        db_action("DELETE FROM expedientes_wf WHERE id = :id", {"id": exp_id})
        
    @staticmethod
    def update_compliance(exp_id, riesgo_aml, origen_fondos, obs, check_pep, check_sanciones):
        db_action("""UPDATE expedientes_wf SET status_comp = 1, riesgo_aml = :r, origen_fondos = :o, 
                     obs_comp = :ob, check_pep = :p, check_sanciones = :s WHERE id = :id""",
                  {"r": riesgo_aml, "o": origen_fondos, "ob": obs, "p": int(check_pep), "s": int(check_sanciones), "id": exp_id})

    @staticmethod
    def update_legal(exp_id, garantias_json, v_garantia, ltv_ratio, fecha_vencimiento_garantia, custodia_fisica, obs_leg):
        db_action("""UPDATE expedientes_wf SET status_leg = 1, garantias_json = :g, v_garantia = :v, 
                     ltv_ratio = :l, fecha_vencimiento_garantia = :fv, custodia_fisica = :c, obs_leg = :ol WHERE id = :id""",
                  {"g": garantias_json, "v": v_garantia, "l": ltv_ratio, "fv": fecha_vencimiento_garantia, 
                   "c": int(custodia_fisica), "ol": obs_leg, "id": exp_id})

    @staticmethod
    def update_riesgo(exp_id, score_f, rm_score, ac, pc, eb, gf, pt, pa, obs_riesgo, cuota_est, ing_mensuales, moneda, estres_aplicado, dscr, margen_ebitda, tasa_sugerida, covenants):
        db_action("""UPDATE expedientes_wf SET status_riesgo = 1, score_f = :s, rm_score = :rm,
                     ac = :ac, pc = :pc, eb = :eb, gf = :gf, pt = :pt, pa = :pa, obs_riesgo = :obs, cuota_est = :ce,
                     ing_mensuales = :im, moneda = :mon, estres_aplicado = :ea, dscr = :d,
                     margen_ebitda = :me, tasa_sugerida = :ts, covenants = :cov WHERE id = :id""",
                  {"s": score_f, "rm": rm_score, "ac": ac, "pc": pc, "eb": eb, "gf": gf, "pt": pt, "pa": pa, 
                   "obs": obs_riesgo, "ce": cuota_est, "im": ing_mensuales, "mon": moneda, "ea": int(estres_aplicado), 
                   "d": dscr, "me": margen_ebitda, "ts": tasa_sugerida, "cov": covenants, "id": exp_id})

    @staticmethod
    def update_dictamen(exp_id, dictamen, aprobado_por, fecha, tasa=0.0, plazo=36):
        if dictamen == 'APROBADO':
            db_action("""UPDATE expedientes_wf SET dictamen = 'APROBADO', tasa_aprobada = :t, 
                         aprobado_por = :a, fecha_decision = :f, plan_generado = 1, plazo_meses = :p WHERE id = :id""", 
                      {"t": tasa, "a": aprobado_por, "f": fecha, "p": plazo, "id": exp_id})
        else:
            db_action("UPDATE expedientes_wf SET dictamen = 'RECHAZADO', aprobado_por = :a, fecha_decision = :f WHERE id = :id", 
                      {"a": aprobado_por, "f": fecha, "id": exp_id})
            
    @staticmethod
    def update_estado_cobranza(exp_id, estado):
        db_action("UPDATE expedientes_wf SET estado_cobranza = :e WHERE id = :id", {"e": estado, "id": exp_id})

class ExpedienteAutomotrizDAO:
    @staticmethod
    def create(fecha, cliente, cedula, monto):
        db_action("INSERT INTO expedientes_auto (fecha, cliente, cedula, monto) VALUES (:f, :c, :r, :m)",
                  {"f": fecha, "c": cliente, "r": cedula, "m": monto})

    @staticmethod
    def get_all_as_df():
        engine = get_connection()
        return pd.read_sql_query(text("SELECT * FROM expedientes_auto"), engine)

    @staticmethod
    def count(dictamen: str = None, cliente: str = None) -> int:
        engine = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_auto')
        with engine.connect() as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM expedientes_auto{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      dictamen: str = None, cliente: str = None) -> pd.DataFrame:
        engine = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_auto')
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM expedientes_auto{where} ORDER BY id DESC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        return pd.read_sql_query(text(query), engine, params=params)
    
    @staticmethod
    def delete(exp_id):
        db_action("DELETE FROM expedientes_auto WHERE id = :id", {"id": exp_id})
        
    @staticmethod
    def update_compliance(exp_id, ocupacion, empleador, telefono, riesgo_aml, origen_fondos, check_pep, check_sanciones, obs):
        db_action("""UPDATE expedientes_auto SET status_comp = 1, ocupacion = :oc, empleador = :em,
                     telefono = :tel, riesgo_aml = :r, origen_fondos = :o, check_pep = :p,
                     check_sanciones = :s, obs_comp = :ob WHERE id = :id""",
                  {"oc": ocupacion, "em": empleador, "tel": telefono, "r": riesgo_aml, "o": origen_fondos, 
                   "p": int(check_pep), "s": int(check_sanciones), "ob": obs, "id": exp_id})

    @staticmethod
    def update_legal(exp_id, marca, modelo, anio, vin, precio_vehiculo, tipo_vehiculo, enganche, plazo_meses, ltv_ratio, seguro_vehiculo, registro_lien, fecha_vencimiento_seguro, obs_leg, vehiculo_placa, seguro_empresa, seguro_poliza, seguro_vigencia):
        db_action("""UPDATE expedientes_auto SET status_leg = 1, marca = :ma, modelo = :mo, anio = :an,
                     vin = :vi, precio_vehiculo = :pv, tipo_vehiculo = :tv, enganche = :en, plazo_meses = :pl,
                     ltv_ratio = :lt, seguro_vehiculo = :sv, registro_lien = :rl,
                     fecha_vencimiento_seguro = :fvs, obs_leg = :ol,
                     vehiculo_placa = :vp, seguro_empresa = :se, seguro_poliza = :sp,
                     seguro_vigencia = :svg WHERE id = :id""",
                  {"ma": marca, "mo": modelo, "an": anio, "vi": vin, "pv": precio_vehiculo, "tv": tipo_vehiculo, 
                   "en": enganche, "pl": plazo_meses, "lt": ltv_ratio, "sv": int(seguro_vehiculo), "rl": int(registro_lien),
                   "fvs": fecha_vencimiento_seguro, "ol": obs_leg, "vp": vehiculo_placa, "se": seguro_empresa, 
                   "sp": seguro_poliza, "svg": seguro_vigencia, "id": exp_id})

    @staticmethod
    def update_riesgo(exp_id, score_f, rm_score, ingreso_mensual, gastos_mensuales, cuota_est, dti_ratio, estabilidad_laboral, estres_aplicado, tasa_sugerida, moneda, obs_riesgo, covenants):
        db_action("""UPDATE expedientes_auto SET status_riesgo = 1, score_f = :s, rm_score = :rm,
                     ingreso_mensual = :im, gastos_mensuales = :gm, cuota_est = :ce, dti_ratio = :dt,
                     estabilidad_laboral = :el, estres_aplicado = :ea, tasa_sugerida = :ts,
                     moneda = :mon, obs_riesgo = :obs, covenants = :cov WHERE id = :id""",
                  {"s": score_f, "rm": rm_score, "im": ingreso_mensual, "gm": gastos_mensuales, "ce": cuota_est, 
                   "dt": dti_ratio, "el": estabilidad_laboral, "ea": int(estres_aplicado), "ts": tasa_sugerida, 
                   "mon": moneda, "obs": obs_riesgo, "cov": covenants, "id": exp_id})

    @staticmethod
    def update_dictamen(exp_id, dictamen, aprobado_por, fecha, tasa=0.0):
        if dictamen == 'APROBADO':
            db_action("""UPDATE expedientes_auto SET dictamen = 'APROBADO', tasa_aprobada = :t, 
                         aprobado_por = :a, fecha_decision = :f, plan_generado = 1 WHERE id = :id""", 
                      {"t": tasa, "a": aprobado_por, "f": fecha, "id": exp_id})
        else:
            db_action("UPDATE expedientes_auto SET dictamen = 'RECHAZADO', aprobado_por = :a, fecha_decision = :f WHERE id = :id", 
                      {"a": aprobado_por, "f": fecha, "id": exp_id})
            
    @staticmethod
    def update_estado_cobranza(exp_id, estado):
        db_action("UPDATE expedientes_auto SET estado_cobranza = :e WHERE id = :id", {"e": estado, "id": exp_id})

class ClienteDAO:
    @staticmethod
    def create(fecha_registro, tipo, nombre, cedula_rif, fecha_nacimiento, nacionalidad, telefono, email, direccion, actividad_economica, nombre_rep, cedula_rep, cargo_rep, docs_json):
        query = """INSERT INTO clientes (fecha_registro,tipo,nombre,cedula_rif,fecha_nacimiento,nacionalidad,
                   telefono,email,direccion,actividad_economica,nombre_rep,cedula_rep,cargo_rep,docs_json,kyc_status) 
                   VALUES (:f,:t,:n,:c,:fn,:nac,:tel,:em,:dir,:act,:nr,:cr,:car,:docs,'Prospecto')"""
        db_action(query, {"f": fecha_registro, "t": tipo, "n": nombre, "c": cedula_rif, "fn": fecha_nacimiento, 
                          "nac": nacionalidad, "tel": telefono, "em": email, "dir": direccion, "act": actividad_economica, 
                          "nr": nombre_rep, "cr": cedula_rep, "car": cargo_rep, "docs": docs_json})

    @staticmethod
    def get_all_as_df():
        engine = get_connection()
        return pd.read_sql_query(text("SELECT * FROM clientes ORDER BY fecha_registro DESC"), engine)

    @staticmethod
    def count(nombre: str = None, tipo: str = None, kyc_status: str = None) -> int:
        engine = get_connection()
        where, params = _build_where({'tipo': tipo, 'kyc_status': kyc_status}, 'clientes')
        if nombre:
            connector = ' AND ' if where else ' WHERE '
            where += f"{connector}(nombre LIKE :n OR cedula_rif LIKE :n)"
            params['n'] = f'%{nombre}%'
        with engine.connect() as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM clientes{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      nombre: str = None, tipo: str = None,
                      kyc_status: str = None) -> pd.DataFrame:
        engine = get_connection()
        where, params = _build_where({'tipo': tipo, 'kyc_status': kyc_status}, 'clientes')
        if nombre:
            connector = ' AND ' if where else ' WHERE '
            where += f"{connector}(nombre LIKE :n OR cedula_rif LIKE :n)"
            params['n'] = f'%{nombre}%'
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM clientes{where} ORDER BY fecha_registro DESC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        return pd.read_sql_query(text(query), engine, params=params)

    @staticmethod
    def update_docs_and_status(cli_id, docs_json, kyc_status):
        db_action("UPDATE clientes SET docs_json = :d, kyc_status = :s WHERE id = :id", {"d": docs_json, "s": kyc_status, "id": cli_id})

    @staticmethod
    def update_kyc_approval(cli_id, obs_kyc, aprobado_por, kyc_fecha):
        db_action("""UPDATE clientes SET kyc_status='KYC Aprobado', obs_kyc = :o, kyc_aprobado_por = :a, kyc_fecha = :f WHERE id = :id""",
                  {"o": obs_kyc, "a": aprobado_por, "f": kyc_fecha, "id": cli_id})

    @staticmethod
    def update_kyc_status(cli_id, status):
        db_action("UPDATE clientes SET kyc_status = :s WHERE id = :id", {"s": status, "id": cli_id})

    @staticmethod
    def update_kyc_observations(cli_id, obs_kyc):
        db_action("UPDATE clientes SET obs_kyc = :o WHERE id = :id", {"o": obs_kyc, "id": cli_id})

class PlanPagoDAO:
    @staticmethod
    def delete_by_expediente(exp_id, tipo):
        db_action("DELETE FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t", {"id": exp_id, "t": tipo})
        
    @staticmethod
    def insert_many(rows):
        # Para insert_many con SQLAlchemy y diccionarios, es más eficiente
        # Pero 'rows' en el código original suele ser una lista de tuplas.
        # SQLAlchemy 2.0 execute() acepta lista de diccionarios.
        # Vamos a convertir las tuplas a diccionarios si es necesario, 
        # o usar el formato posicional si el engine lo permite.
        # Dado que insert_many se usa con executemany, SQLAlchemy lo maneja bien con lista de tuplas si no usamos text() con nombres.
        # Pero como usamos text(), usaremos parámetros nombrados.
        query = text("""INSERT INTO plan_pagos (expediente_id, tipo_expediente, periodo, fecha_pago, cuota, capital, interes, saldo, estado) 
                        VALUES (:eid, :te, :per, :fp, :cuo, :cap, :int, :sal, :est)""")
        
        # Convertir lista de tuplas a lista de dicts para compatibilidad total con text()
        formatted_rows = []
        for r in rows:
            formatted_rows.append({
                "eid": r[0], "te": r[1], "per": r[2], "fp": r[3],
                "cuo": r[4], "cap": r[5], "int": r[6], "sal": r[7], "est": r[8]
            })
            
        engine = get_connection()
        with engine.begin() as conn:
            conn.execute(query, formatted_rows)

    @staticmethod
    def get_by_expediente(exp_id, tipo):
        engine = get_connection()
        df = pd.read_sql_query(text("SELECT * FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t ORDER BY periodo"), 
                               engine, params={"id": exp_id, "t": tipo})
        return df.to_dict('records')

    @staticmethod
    def get_by_expediente_as_df(exp_id, tipo):
        engine = get_connection()
        query = text("SELECT periodo AS [N°], fecha_pago AS [Fecha], cuota AS [Cuota], capital AS [Capital], interes AS [Interés], saldo AS [Saldo] FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t ORDER BY periodo")
        return pd.read_sql_query(query, engine, params={"id": exp_id, "t": tipo})

    @staticmethod
    def mark_as_paid(plan_id):
        db_action("UPDATE plan_pagos SET estado='PAGADO' WHERE id = :id", {"id": plan_id})
        
    @staticmethod
    def get_all_as_df():
        engine = get_connection()
        return pd.read_sql_query(text("SELECT * FROM plan_pagos ORDER BY fecha_pago"), engine)

    @staticmethod
    def count(expediente_id: int = None, tipo: str = None, estado: str = None) -> int:
        engine = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo, 'estado': estado},
            'plan_pagos')
        with engine.connect() as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM plan_pagos{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 15,
                      expediente_id: int = None, tipo: str = None,
                      estado: str = None) -> pd.DataFrame:
        engine = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo, 'estado': estado},
            'plan_pagos')
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM plan_pagos{where} ORDER BY fecha_pago OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        return pd.read_sql_query(text(query), engine, params=params)

class GestionCobranzaDAO:
    @staticmethod
    def create(exp_id, tipo, fecha, tipo_gestion, responsable, resultado, prox_accion, fecha_prox, obs):
        db_action("""INSERT INTO gestiones_cobranza (expediente_id, tipo_expediente, fecha, tipo_gestion, 
                     responsable, resultado, proxima_accion, fecha_proxima, obs) 
                     VALUES (:id, :t, :f, :tg, :res, :resu, :pa, :fp, :o)""",
                  {"id": exp_id, "t": tipo, "f": fecha, "tg": tipo_gestion, "res": responsable, 
                   "resu": resultado, "pa": prox_accion, "fp": fecha_prox, "o": obs})

    @staticmethod
    def get_all_as_df():
        engine = get_connection()
        return pd.read_sql_query(text("SELECT * FROM gestiones_cobranza ORDER BY fecha DESC"), engine)

    @staticmethod
    def count(expediente_id: int = None, tipo: str = None) -> int:
        engine = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo}, 'gestiones_cobranza')
        with engine.connect() as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM gestiones_cobranza{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 15,
                      expediente_id: int = None, tipo: str = None) -> pd.DataFrame:
        engine = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo}, 'gestiones_cobranza')
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM gestiones_cobranza{where} ORDER BY fecha DESC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        return pd.read_sql_query(text(query), engine, params=params)

class PagoRecibidoDAO:
    @staticmethod
    def create(exp_id, tipo, fecha_pago, monto, referencia):
        db_action("""INSERT INTO pagos_recibidos (expediente_id, tipo_expediente, fecha_pago, monto, referencia) 
                     VALUES (:id, :t, :f, :m, :r)""",
                  {"id": exp_id, "t": tipo, "f": fecha_pago, "m": monto, "r": referencia})
