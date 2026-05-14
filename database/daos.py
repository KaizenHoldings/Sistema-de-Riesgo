import pandas as pd
import streamlit as st
from .db_core import get_connection, db_action
from .models import Usuario


def _build_where(filters: dict, _table: str = "") -> tuple:
    """
    Construye dinámicamente una cláusula WHERE y su lista de parámetros
    a partir de un dict {columna: valor}. Los valores None son ignorados.
    """
    clauses = [f"{col} = ?" for col, val in filters.items() if val is not None]
    params  = tuple(val for val in filters.values() if val is not None)
    where   = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params



class UsuarioDAO:
    @staticmethod
    def get_by_credentials(user, password):
        conn = get_connection()
        curr = conn.cursor()
        curr.execute("SELECT * FROM usuarios WHERE user=? AND password=?", (user, password))
        row = curr.fetchone()
        conn.close()
        if row:
            return Usuario(user=row[0], password=row[1], role=row[2])
        return None

    @staticmethod
    def upsert(user, password, role):
        db_action("INSERT OR REPLACE INTO usuarios VALUES (?,?,?)", (user, password, role))

    @staticmethod
    def update_password(user, new_password):
        db_action("UPDATE usuarios SET password=? WHERE user=?", (new_password, user))

    @staticmethod
    def get_all_as_df():
        conn = get_connection()
        df = pd.read_sql_query("SELECT user AS Usuario, role AS Rol FROM usuarios", conn)
        conn.close()
        return df

class ConfigParametroDAO:
    @staticmethod
    @st.cache_data
    def get_all_as_dict():
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM config_parametros", conn)
        conn.close()
        return dict(zip(df['clave'], df['valor']))

    @staticmethod
    def update_param(clave, valor):
        db_action("UPDATE config_parametros SET valor=? WHERE clave=?", (valor, clave))

class ExpedienteCorporativoDAO:
    @staticmethod
    def create(fecha, cliente, rif, monto):
        db_action("INSERT INTO expedientes_wf (fecha, cliente, rif, monto) VALUES (?,?,?,?)",
                  (fecha, cliente, rif, monto))

    @staticmethod
    def get_all_as_df():
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM expedientes_wf", conn)
        conn.close()
        return df

    @staticmethod
    def count(dictamen: str = None, cliente: str = None) -> int:
        """Retorna el total de expedientes aplicando filtros opcionales."""
        conn = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_wf')
        row = conn.execute(f"SELECT COUNT(*) FROM expedientes_wf{where}", params).fetchone()
        conn.close()
        return row[0]

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      dictamen: str = None, cliente: str = None) -> pd.DataFrame:
        """Consulta paginada con LIMIT/OFFSET y filtros opcionales."""
        conn = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_wf')
        offset = (page - 1) * page_size
        df = pd.read_sql_query(
            f"SELECT * FROM expedientes_wf{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            conn, params=(*params, page_size, offset))
        conn.close()
        return df
    
    @staticmethod
    def delete(exp_id):
        db_action("DELETE FROM expedientes_wf WHERE id=?", (exp_id,))
        
    @staticmethod
    def update_compliance(exp_id, riesgo_aml, origen_fondos, obs, check_pep, check_sanciones):
        db_action("UPDATE expedientes_wf SET status_comp=1, riesgo_aml=?, origen_fondos=?, obs_comp=?, check_pep=?, check_sanciones=? WHERE id=?",
                  (riesgo_aml, origen_fondos, obs, int(check_pep), int(check_sanciones), exp_id))

    @staticmethod
    def update_legal(exp_id, garantias_json, v_garantia, ltv_ratio, fecha_vencimiento_garantia, custodia_fisica, obs_leg):
        db_action("UPDATE expedientes_wf SET status_leg=1, garantias_json=?, v_garantia=?, ltv_ratio=?, fecha_vencimiento_garantia=?, custodia_fisica=?, obs_leg=? WHERE id=?",
                  (garantias_json, v_garantia, ltv_ratio, fecha_vencimiento_garantia, int(custodia_fisica), obs_leg, exp_id))

    @staticmethod
    def update_riesgo(exp_id, score_f, rm_score, ac, pc, eb, gf, pt, pa, obs_riesgo, cuota_est, ing_mensuales, moneda, estres_aplicado, dscr, margen_ebitda, tasa_sugerida, covenants):
        db_action("""UPDATE expedientes_wf SET status_riesgo=1, score_f=?, rm_score=?,
                     ac=?, pc=?, eb=?, gf=?, pt=?, pa=?, obs_riesgo=?, cuota_est=?,
                     ing_mensuales=?, moneda=?, estres_aplicado=?, dscr=?,
                     margen_ebitda=?, tasa_sugerida=?, covenants=? WHERE id=?""",
                  (score_f, rm_score, ac, pc, eb, gf, pt, pa, obs_riesgo, cuota_est,
                   ing_mensuales, moneda, int(estres_aplicado), dscr, margen_ebitda,
                   tasa_sugerida, covenants, exp_id))



    @staticmethod
    def update_dictamen(exp_id, dictamen, aprobado_por, fecha, tasa=0.0, plazo=36):
        if dictamen == 'APROBADO':
            db_action("UPDATE expedientes_wf SET dictamen='APROBADO', tasa_aprobada=?, aprobado_por=?, fecha_decision=?, plan_generado=1, plazo_meses=? WHERE id=?", 
                      (tasa, aprobado_por, fecha, plazo, exp_id))
        else:
            db_action("UPDATE expedientes_wf SET dictamen='RECHAZADO', aprobado_por=?, fecha_decision=? WHERE id=?", 
                      (aprobado_por, fecha, exp_id))
            
    @staticmethod
    def update_estado_cobranza(exp_id, estado):
        db_action("UPDATE expedientes_wf SET estado_cobranza=? WHERE id=?", (estado, exp_id))

class ExpedienteAutomotrizDAO:
    @staticmethod
    def create(fecha, cliente, cedula, monto):
        db_action("INSERT INTO expedientes_auto (fecha, cliente, cedula, monto) VALUES (?,?,?,?)",
                  (fecha, cliente, cedula, monto))

    @staticmethod
    def get_all_as_df():
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM expedientes_auto", conn)
        conn.close()
        return df

    @staticmethod
    def count(dictamen: str = None, cliente: str = None) -> int:
        conn = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_auto')
        row = conn.execute(f"SELECT COUNT(*) FROM expedientes_auto{where}", params).fetchone()
        conn.close()
        return row[0]

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      dictamen: str = None, cliente: str = None) -> pd.DataFrame:
        conn = get_connection()
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_auto')
        offset = (page - 1) * page_size
        df = pd.read_sql_query(
            f"SELECT * FROM expedientes_auto{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            conn, params=(*params, page_size, offset))
        conn.close()
        return df
    
    @staticmethod
    def delete(exp_id):
        db_action("DELETE FROM expedientes_auto WHERE id=?", (exp_id,))
        
    @staticmethod
    def update_compliance(exp_id, ocupacion, empleador, telefono, riesgo_aml, origen_fondos, check_pep, check_sanciones, obs):
        db_action("""UPDATE expedientes_auto SET status_comp=1, ocupacion=?, empleador=?,
                     telefono=?, riesgo_aml=?, origen_fondos=?, check_pep=?,
                     check_sanciones=?, obs_comp=? WHERE id=?""",
                  (ocupacion, empleador, telefono, riesgo_aml, origen_fondos, int(check_pep), int(check_sanciones), obs, exp_id))

    @staticmethod
    def update_legal(exp_id, marca, modelo, anio, vin, precio_vehiculo, tipo_vehiculo, enganche, plazo_meses, ltv_ratio, seguro_vehiculo, registro_lien, fecha_vencimiento_seguro, obs_leg, vehiculo_placa, seguro_empresa, seguro_poliza, seguro_vigencia):
        db_action("""UPDATE expedientes_auto SET status_leg=1, marca=?, modelo=?, anio=?,
                     vin=?, precio_vehiculo=?, tipo_vehiculo=?, enganche=?, plazo_meses=?,
                     ltv_ratio=?, seguro_vehiculo=?, registro_lien=?,
                     fecha_vencimiento_seguro=?, obs_leg=?,
                     vehiculo_placa=?, seguro_empresa=?, seguro_poliza=?,
                     seguro_vigencia=? WHERE id=?""",
                  (marca, modelo, anio, vin, precio_vehiculo, tipo_vehiculo, enganche, plazo_meses,
                   ltv_ratio, int(seguro_vehiculo), int(registro_lien),
                   fecha_vencimiento_seguro, obs_leg,
                   vehiculo_placa, seguro_empresa, seguro_poliza,
                   seguro_vigencia, exp_id))

    @staticmethod
    def update_riesgo(exp_id, score_f, rm_score, ingreso_mensual, gastos_mensuales, cuota_est, dti_ratio, estabilidad_laboral, estres_aplicado, tasa_sugerida, moneda, obs_riesgo, covenants):
        db_action("""UPDATE expedientes_auto SET status_riesgo=1, score_f=?, rm_score=?,
                     ingreso_mensual=?, gastos_mensuales=?, cuota_est=?, dti_ratio=?,
                     estabilidad_laboral=?, estres_aplicado=?, tasa_sugerida=?,
                     moneda=?, obs_riesgo=?, covenants=? WHERE id=?""",
                  (score_f, rm_score, ingreso_mensual, gastos_mensuales, cuota_est, dti_ratio,
                   estabilidad_laboral, int(estres_aplicado), tasa_sugerida, moneda,
                   obs_riesgo, covenants, exp_id))



    @staticmethod
    def update_dictamen(exp_id, dictamen, aprobado_por, fecha, tasa=0.0):
        if dictamen == 'APROBADO':
            db_action("UPDATE expedientes_auto SET dictamen='APROBADO', tasa_aprobada=?, aprobado_por=?, fecha_decision=?, plan_generado=1 WHERE id=?", 
                      (tasa, aprobado_por, fecha, exp_id))
        else:
            db_action("UPDATE expedientes_auto SET dictamen='RECHAZADO', aprobado_por=?, fecha_decision=? WHERE id=?", 
                      (aprobado_por, fecha, exp_id))
            
    @staticmethod
    def update_estado_cobranza(exp_id, estado):
        db_action("UPDATE expedientes_auto SET estado_cobranza=? WHERE id=?", (estado, exp_id))

class ClienteDAO:
    @staticmethod
    def create(fecha_registro, tipo, nombre, cedula_rif, fecha_nacimiento, nacionalidad, telefono, email, direccion, actividad_economica, nombre_rep, cedula_rep, cargo_rep, docs_json):
        query = """INSERT INTO clientes (fecha_registro,tipo,nombre,cedula_rif,fecha_nacimiento,nacionalidad,
                   telefono,email,direccion,actividad_economica,nombre_rep,cedula_rep,cargo_rep,docs_json,kyc_status) 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'Prospecto')"""
        db_action(query, (fecha_registro, tipo, nombre, cedula_rif, fecha_nacimiento, nacionalidad, telefono, email, direccion, actividad_economica, nombre_rep, cedula_rep, cargo_rep, docs_json))

    @staticmethod
    def get_all_as_df():
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM clientes ORDER BY fecha_registro DESC", conn)
        conn.close()
        return df

    @staticmethod
    def count(nombre: str = None, tipo: str = None, kyc_status: str = None) -> int:
        conn = get_connection()
        where, params = _build_where({'tipo': tipo, 'kyc_status': kyc_status}, 'clientes')
        if nombre:
            connector = ' AND ' if where else ' WHERE '
            where += f"{connector}(nombre LIKE ? OR cedula_rif LIKE ?)"
            params = (*params, f'%{nombre}%', f'%{nombre}%')
        row = conn.execute(f"SELECT COUNT(*) FROM clientes{where}", params).fetchone()
        conn.close()
        return row[0]

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      nombre: str = None, tipo: str = None,
                      kyc_status: str = None) -> pd.DataFrame:
        conn = get_connection()
        where, params = _build_where({'tipo': tipo, 'kyc_status': kyc_status}, 'clientes')
        if nombre:
            connector = ' AND ' if where else ' WHERE '
            where += f"{connector}(nombre LIKE ? OR cedula_rif LIKE ?)"
            params = (*params, f'%{nombre}%', f'%{nombre}%')
        offset = (page - 1) * page_size
        df = pd.read_sql_query(
            f"SELECT * FROM clientes{where} ORDER BY fecha_registro DESC LIMIT ? OFFSET ?",
            conn, params=(*params, page_size, offset))
        conn.close()
        return df

    @staticmethod
    def update_docs_and_status(cli_id, docs_json, kyc_status):
        db_action("UPDATE clientes SET docs_json=?, kyc_status=? WHERE id=?", (docs_json, kyc_status, cli_id))

    @staticmethod
    def update_kyc_approval(cli_id, obs_kyc, aprobado_por, kyc_fecha):
        db_action("""UPDATE clientes SET kyc_status='KYC Aprobado', obs_kyc=?, kyc_aprobado_por=?, kyc_fecha=? WHERE id=?""",
                  (obs_kyc, aprobado_por, kyc_fecha, cli_id))

    @staticmethod
    def update_kyc_status(cli_id, status):
        db_action("UPDATE clientes SET kyc_status=? WHERE id=?", (status, cli_id))

    @staticmethod
    def update_kyc_observations(cli_id, obs_kyc):
        db_action("UPDATE clientes SET obs_kyc=? WHERE id=?", (obs_kyc, cli_id))

class PlanPagoDAO:
    @staticmethod
    def delete_by_expediente(exp_id, tipo):
        db_action("DELETE FROM plan_pagos WHERE expediente_id=? AND tipo_expediente=?", (exp_id, tipo))
        
    @staticmethod
    def insert_many(rows):
        conn = get_connection()
        c = conn.cursor()
        c.executemany(
            "INSERT INTO plan_pagos (expediente_id, tipo_expediente, periodo, fecha_pago, cuota, capital, interes, saldo, estado) VALUES (?,?,?,?,?,?,?,?,?)",
            rows)
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_expediente(exp_id, tipo):
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM plan_pagos WHERE expediente_id=? AND tipo_expediente=? ORDER BY periodo", conn, params=(exp_id, tipo))
        conn.close()
        return df.to_dict('records')

    @staticmethod
    def get_by_expediente_as_df(exp_id, tipo):
        conn = get_connection()
        query = "SELECT periodo AS 'N°', fecha_pago AS 'Fecha', cuota AS 'Cuota', capital AS 'Capital', interes AS 'Interés', saldo AS 'Saldo' FROM plan_pagos WHERE expediente_id=? AND tipo_expediente=? ORDER BY periodo"
        df = pd.read_sql_query(query, conn, params=(exp_id, tipo))
        conn.close()
        return df

    @staticmethod
    def mark_as_paid(plan_id):
        db_action("UPDATE plan_pagos SET estado='PAGADO' WHERE id=?", (plan_id,))
        
    @staticmethod
    def get_all_as_df():
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM plan_pagos ORDER BY fecha_pago", conn)
        conn.close()
        return df

    @staticmethod
    def count(expediente_id: int = None, tipo: str = None, estado: str = None) -> int:
        conn = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo, 'estado': estado},
            'plan_pagos')
        row = conn.execute(f"SELECT COUNT(*) FROM plan_pagos{where}", params).fetchone()
        conn.close()
        return row[0]

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 15,
                      expediente_id: int = None, tipo: str = None,
                      estado: str = None) -> pd.DataFrame:
        conn = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo, 'estado': estado},
            'plan_pagos')
        offset = (page - 1) * page_size
        df = pd.read_sql_query(
            f"SELECT * FROM plan_pagos{where} ORDER BY fecha_pago LIMIT ? OFFSET ?",
            conn, params=(*params, page_size, offset))
        conn.close()
        return df

class GestionCobranzaDAO:
    @staticmethod
    def create(exp_id, tipo, fecha, tipo_gestion, responsable, resultado, prox_accion, fecha_prox, obs):
        db_action("INSERT INTO gestiones_cobranza (expediente_id, tipo_expediente, fecha, tipo_gestion, responsable, resultado, proxima_accion, fecha_proxima, obs) VALUES (?,?,?,?,?,?,?,?,?)",
                  (exp_id, tipo, fecha, tipo_gestion, responsable, resultado, prox_accion, fecha_prox, obs))

    @staticmethod
    def get_all_as_df():
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM gestiones_cobranza ORDER BY fecha DESC", conn)
        conn.close()
        return df

    @staticmethod
    def count(expediente_id: int = None, tipo: str = None) -> int:
        conn = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo}, 'gestiones_cobranza')
        row = conn.execute(f"SELECT COUNT(*) FROM gestiones_cobranza{where}", params).fetchone()
        conn.close()
        return row[0]

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 15,
                      expediente_id: int = None, tipo: str = None) -> pd.DataFrame:
        conn = get_connection()
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo}, 'gestiones_cobranza')
        offset = (page - 1) * page_size
        df = pd.read_sql_query(
            f"SELECT * FROM gestiones_cobranza{where} ORDER BY fecha DESC LIMIT ? OFFSET ?",
            conn, params=(*params, page_size, offset))
        conn.close()
        return df

class PagoRecibidoDAO:
    @staticmethod
    def create(exp_id, tipo, fecha_pago, monto, referencia):
        db_action("INSERT INTO pagos_recibidos (expediente_id, tipo_expediente, fecha_pago, monto, referencia) VALUES (?,?,?,?,?)",
                  (exp_id, tipo, fecha_pago, monto, referencia))
