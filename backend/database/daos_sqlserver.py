from datetime import datetime
from functools import lru_cache
from sqlalchemy import text
from .db_core_sqlserver import get_connection, db_action, sesion_activa


def _filas(conn, consulta, params=None):
    """
    Materializa el resultado de una consulta como lista de diccionarios.

    Sustituye a `pd.read_sql_query`: la capa de datos ya no depende de pandas y
    devuelve estructuras serializables tal cual. Las vistas que necesiten un
    DataFrame lo construyen en su propio ámbito.
    """
    filas = conn.execute(consulta, params or {}).mappings().all()
    return [dict(f) for f in filas]
from .models import Usuario
from services.security_service import SecurityService

def _build_where(filters: dict, _table: str = "") -> tuple:
    """
    Construye dinámicamente una cláusula WHERE y su diccionario de parámetros
    usando marcadores nombrados para SQLAlchemy.

    Un valor escalar genera `columna = :pN`. Una lista, tupla o conjunto genera
    `columna IN (:pN_0, :pN_1, ...)`, con un marcador nombrado por elemento, de
    modo que los valores nunca se interpolan en la cadena SQL.
    """
    clauses = []
    params = {}
    for i, (col, val) in enumerate(filters.items()):
        if val is None:
            continue

        if isinstance(val, (list, tuple, set)):
            valores = [v for v in val if v is not None]
            if not valores:
                continue
            marcadores = []
            for j, v in enumerate(valores):
                nombre = f"p{i}_{j}"
                marcadores.append(f":{nombre}")
                params[nombre] = v
            clauses.append(f"{col} IN ({', '.join(marcadores)})")
        else:
            param_name = f"p{i}"
            clauses.append(f"{col} = :{param_name}")
            params[param_name] = val

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def _append_cond(where: str, cond: str) -> str:
    """Anexa una condicion al WHERE ya construido, eligiendo WHERE o AND."""
    if not cond:
        return where
    connector = " AND " if where else " WHERE "
    return f"{where}{connector}{cond}"


def _append_activos(where: str) -> str:
    """Excluye los expedientes con borrado logico (eliminado = 1)."""
    return _append_cond(where, "eliminado = 0")


def _append_firmas(where: str, firmas_completas: bool = None) -> str:
    """
    Anexa la condicion de firmas al WHERE ya construido por `_build_where`.

    True  -> las tres firmas registradas.
    False -> al menos una firma pendiente.
    None  -> sin filtro (devuelve el WHERE intacto).

    Usa literales 0/1, asi que no altera el diccionario de parametros ni el
    patron de SQL parametrizado del resto de la capa.
    """
    if firmas_completas is None:
        return where
    if firmas_completas:
        cond = "status_comp = 1 AND status_leg = 1 AND status_riesgo = 1"
    else:
        cond = "(status_comp = 0 OR status_leg = 0 OR status_riesgo = 0)"
    return _append_cond(where, cond)


# ── Visibilidad por rol aprobador ─────────────────────────────────────
# Cada firmante ve lo que le compete: lo que espera su firma y lo que ya firmó.
# Cumplimiento abre el circuito, así que no se le filtra nada; los roles que no
# firman —Comercial, Cobranzas, Superadmin— tampoco.
VISIBILIDAD_APROBADOR = {
    'Legal': "(status_comp = 1 OR status_leg = 1)",
    'Riesgo': "(status_comp = 1 OR status_riesgo = 1)",
    'Comité': ("((status_comp = 1 AND status_leg = 1 AND status_riesgo = 1)"
               " OR dictamen <> 'PENDIENTE')"),
}



# ── Pestañas de la bandeja, por rol ───────────────────────────────────
# Cada firmante mide «pendiente» por su propia firma: lo que aún no ha firmado
# frente a lo que ya firmó. El Comité decide al final, así que lo suyo es lo que
# llega con las tres firmas y sin dictamen. Quien no firma —Comercial,
# Superadmin— sigue la solicitud entera: abierta o ya resuelta.
#
# En la base, «denegado» es dictamen = 'RECHAZADO' y «frenado» son las
# devoluciones, que se guardan como 'REVISIÓN-<etapa>'. Las dos son dictámenes
# distintos de 'PENDIENTE', así que el histórico las recoge sin enumerarlas.
# La bandeja de pendientes respeta el orden del circuito: Legal y Riesgo solo
# ven lo que Cumplimiento ya certifico, porque antes de esa firma el expediente
# todavia no ha llegado a su etapa. Y ninguna pestana de pendientes muestra
# expedientes con dictamen: aprobados, denegados o frenados no esperan firma.
# Un expediente parado y devuelto al area comercial. En la base, el rechazo es
# 'RECHAZADO' y las devoluciones se guardan como 'REVISION-<etapa>'; los otros
# nombres se aceptan por si el dictamen llega escrito con la nomenclatura del
# negocio.
VUELTAS_ATRAS = ("(dictamen IN ('RECHAZADO', 'DENEGADO', 'FRENADO', 'DEVUELTO')"
                 " OR dictamen LIKE 'REVISI%')")

# Un expediente ya reevaluado deja de estar en la bandeja: su continuacion es el
# hijo que lo referencia, y mantener los dos invitaria a trabajar sobre el que
# ya no vale. El marcador {t} lo rellena `_append_vista` con la tabla en curso.
SIN_REEVALUAR = ("NOT EXISTS (SELECT 1 FROM {t} hijo"
                 " WHERE hijo.parent_expediente_id = {t}.id)")

VISTA_POR_ROL = {
    ('Compliance', 'pending'): "(dictamen = 'PENDIENTE' AND status_comp = 0)",
    ('Compliance', 'history'): "status_comp = 1",
    ('Legal', 'pending'): ("(dictamen = 'PENDIENTE' AND status_comp = 1"
                           " AND status_leg = 0)"),
    ('Legal', 'history'): "status_leg = 1",
    ('Riesgo', 'pending'): ("(dictamen = 'PENDIENTE' AND status_comp = 1"
                            " AND status_riesgo = 0)"),
    ('Riesgo', 'history'): "status_riesgo = 1",
    ('Comité', 'pending'): ("(status_comp = 1 AND status_leg = 1 AND status_riesgo = 1"
                            " AND dictamen = 'PENDIENTE')"),
    ('Comité', 'history'): "dictamen <> 'PENDIENTE'",
    # Comercial no evalua: su bandeja son las solicitudes que se le devuelven
    # para subsanar. Lo demas sigue su curso sin que tenga nada que hacer.
    ('Comercial', 'pending'): VUELTAS_ATRAS + " AND " + SIN_REEVALUAR,
}

# Comercial, Superadmin y cualquier rol sin reglas propias.
VISTA_POR_DEFECTO = {
    'pending': "dictamen = 'PENDIENTE'",
    'history': "dictamen <> 'PENDIENTE'",
}


# Roles a los que 'all' les abre la cartera entera: no firman etapas, siguen
# solicitudes, y perder de vista las que avanzan seria perder la trazabilidad.
ROLES_VISTA_COMPLETA = ('Comercial', 'Superadmin')


def _append_vista(where: str, rol: str = None, modo: str = None,
                  tabla: str = 'expedientes_wf') -> str:
    """
    Anexa la condicion de la pestaña pedida.

    Sin `modo` no hay pestaña: se conserva el recorte por rol de siempre, que
    evita que un firmante vea expedientes que aun no han llegado a su etapa.

    `all` devuelve la cartera completa a quien la necesita para seguimiento; a
    un firmante le deja su recorte de siempre, porque su bandeja no es un
    listado general.
    """
    if not modo:
        return _append_visibilidad(where, rol)
    if modo == 'all':
        if (rol or '') in ROLES_VISTA_COMPLETA:
            return where
        return _append_visibilidad(where, rol)
    condicion = (VISTA_POR_ROL.get((rol or '', modo))
                 or VISTA_POR_DEFECTO.get(modo, ''))
    # La tabla es una constante del DAO que llama, nunca un dato de entrada.
    return _append_cond(where, condicion.format(t=tabla))


def _append_visibilidad(where: str, rol: str = None) -> str:
    """Anexa la condicion de visibilidad del rol, si tiene una definida."""
    return _append_cond(where, VISIBILIDAD_APROBADOR.get(rol or '', ''))


# Columnas que viajan del expediente devuelto al nuevo: identidad del cliente y
# condiciones comerciales. Todo lo demas —firmas, dictamen, observaciones y
# cifras de evaluacion— nace vacio, que es lo que hace del clon una reevaluacion
# y no una copia del veredicto anterior.
COLUMNAS_CLONABLES_CORP = (
    'cliente', 'rif', 'monto', 'cliente_id', 'descripcion',
    'plazo_meses', 'moneda', 'tipo_producto',
)

COLUMNAS_CLONABLES_AUTO = (
    'cliente', 'cedula', 'ocupacion', 'empleador', 'telefono',
    'marca', 'modelo', 'anio', 'vin', 'vehiculo_placa',
    'precio_vehiculo', 'tipo_vehiculo', 'monto', 'plazo_meses', 'enganche',
    'moneda', 'cliente_id', 'descripcion', 'tipo_producto',
)


def _clonar_expediente(tabla, columnas, exp_id, fecha, session):
    """
    Crea el expediente hijo y devuelve su id, o None si el padre no existe.

    El id se pide con OUTPUT dentro de la misma sentencia y no con
    SCOPE_IDENTITY aparte: una segunda consulta seria otro ambito y devolveria
    NULL.
    """
    cols = ', '.join(columnas)
    consulta = text(
        "INSERT INTO {t} (fecha, parent_expediente_id, {c}) OUTPUT INSERTED.id "
        "SELECT :fecha, id, {c} FROM {t} WHERE id = :id AND eliminado = 0".format(
            t=tabla, c=cols))
    with sesion_activa(session) as s:
        fila = s.execute(consulta, {'fecha': fecha, 'id': exp_id}).fetchone()
    return int(fila[0]) if fila else None


class UsuarioDAO:
    @staticmethod
    def get_by_credentials(user, password, session=None):
        with sesion_activa(session) as conn:
            query = text("SELECT * FROM usuarios WHERE [user] = :u")
            row = conn.execute(query, {"u": user}).fetchone()
            
            if row:
                stored_hash = row[1]
                if SecurityService.verify_password(password, stored_hash):
                    return Usuario(user=row[0], password=stored_hash, role=row[2])
        return None

    @staticmethod
    def upsert(user, password, role, session=None):
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
        db_action(query, {"u": user, "p": hashed_password, "r": role}, session=session)

    @staticmethod
    def update_password(user, new_password, session=None):
        hashed_password = SecurityService.hash_password(new_password)
        db_action("UPDATE usuarios SET [password] = :p WHERE [user] = :u", {"p": hashed_password, "u": user}, session=session)

    @staticmethod
    def get_all(session=None):
        """Usuarios como lista de diccionarios con las claves Usuario y Rol."""
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT [user] AS Usuario, [role] AS Rol FROM usuarios"))


@lru_cache(maxsize=1)
def _leer_parametros():
    """
    Lectura cacheada de `config_parametros`.

    Antes vivía bajo `@st.cache_data`, lo que obligaba a importar Streamlit en la
    capa de datos. Con `lru_cache` la caché es del proceso y se invalida de forma
    explícita al actualizar un parámetro.
    """
    with sesion_activa() as s:
        filas = _filas(s, text("SELECT * FROM config_parametros"))
    return {f['clave']: f['valor'] for f in filas}


# Las vistas invalidan con `get_all_as_dict.clear()`, que era la firma de
# Streamlit. Se conserva ese nombre como alias de `cache_clear` para no
# obligarlas a cambiar.
_leer_parametros.clear = _leer_parametros.cache_clear


class ConfigParametroDAO:
    # Se expone la función cacheada tal cual: conserva `.clear()` y `.cache_clear()`
    get_all_as_dict = staticmethod(_leer_parametros)

    @staticmethod
    def update_param(clave, valor, session=None):
        db_action("UPDATE config_parametros SET valor = :v WHERE clave = :k", {"v": valor, "k": clave}, session=session)
        # Sin TTL, un parámetro actualizado quedaría cacheado indefinidamente
        _leer_parametros.cache_clear()

class ExpedienteCorporativoDAO:
    @staticmethod
    def create(fecha, cliente, rif, monto, cliente_id=None, descripcion="", session=None):
        db_action("INSERT INTO expedientes_wf (fecha, cliente, rif, monto, cliente_id, descripcion) VALUES (:f, :c, :r, :m, :cid, :desc)",
                  {"f": fecha, "c": cliente, "r": rif, "m": monto, "cid": cliente_id, "desc": descripcion}, session=session)

    @staticmethod
    def get_all(session=None):
        """Expedientes corporativos activos como lista de diccionarios."""
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT * FROM expedientes_wf WHERE eliminado = 0"))

    @staticmethod
    def get_by_id(exp_id, session=None):
        if exp_id is None:
            return None
        with sesion_activa(session) as conn:
            query = text("SELECT * FROM expedientes_wf WHERE id = :id AND eliminado = 0")
            row = conn.execute(query, {"id": exp_id}).fetchone()
            if row:
                return dict(row._mapping)
        return None

    @staticmethod
    def count(dictamen: str = None, cliente: str = None,
              status_comp: int = None, status_leg: int = None, status_riesgo: int = None,
              firmas_completas: bool = None, rol_visibilidad: str = None,
              modo_vista: str = None, session=None) -> int:
        filters = {
            'dictamen': dictamen,
            'cliente': cliente,
            'status_comp': status_comp,
            'status_leg': status_leg,
            'status_riesgo': status_riesgo
        }

        where, params = _build_where(filters, 'expedientes_wf')
        where = _append_firmas(where, firmas_completas)
        where = _append_vista(where, rol_visibilidad, modo_vista, 'expedientes_wf')
        where = _append_activos(where)
        with sesion_activa(session) as conn:
           
            res = conn.execute(text(f"SELECT COUNT(*) FROM expedientes_wf{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      dictamen: str = None, cliente: str = None,
                      firmas_completas: bool = None, rol_visibilidad: str = None,
                      modo_vista: str = None, session=None) -> list:
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_wf')
        where = _append_firmas(where, firmas_completas)
        where = _append_vista(where, rol_visibilidad, modo_vista, 'expedientes_wf')
        where = _append_activos(where)
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM expedientes_wf{where} ORDER BY id ASC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        with sesion_activa(session) as s:
            return _filas(s, text(query), params)

    @staticmethod
    def get_resumen_por_dictamen(session=None) -> dict:
        """
        Conteo y monto agregados por dictamen, resueltos con GROUP BY en el motor.

        Returns:
            dict {dictamen: {'n': int, 'monto': float}} solo con los dictamenes
            presentes; el consumidor debe usar .get() con valores por defecto.
        """
        query = text("""SELECT dictamen, COUNT(*) AS n, SUM(monto) AS monto
                        FROM expedientes_wf WHERE eliminado = 0 GROUP BY dictamen""")
        with sesion_activa(session) as conn:
            filas = conn.execute(query).fetchall()
        return {f[0]: {'n': int(f[1] or 0), 'monto': float(f[2] or 0.0)} for f in filas}

    @staticmethod
    def delete(exp_id, session=None):
        db_action("UPDATE expedientes_wf SET eliminado = 1 WHERE id = :id", {"id": exp_id}, session=session)
        
    @staticmethod
    def update_compliance(exp_id, riesgo_aml, origen_fondos, obs, check_pep, check_sanciones, session=None):
        db_action("""UPDATE expedientes_wf SET status_comp = 1, riesgo_aml = :r, origen_fondos = :o, 
                     obs_comp = :ob, check_pep = :p, check_sanciones = :s WHERE id = :id""",
                  {"r": riesgo_aml, "o": origen_fondos, "ob": obs, "p": int(check_pep), "s": int(check_sanciones), "id": exp_id}, session=session)

    @staticmethod
    def update_legal(exp_id, garantias_json, v_garantia, ltv_ratio, fecha_vencimiento_garantia, custodia_fisica, obs_leg, session=None):
        db_action("""UPDATE expedientes_wf SET status_leg = 1, garantias_json = :g, v_garantia = :v, 
                     ltv_ratio = :l, fecha_vencimiento_garantia = :fv, custodia_fisica = :c, obs_leg = :ol WHERE id = :id""",
                  {"g": garantias_json, "v": v_garantia, "l": ltv_ratio, "fv": fecha_vencimiento_garantia, 
                   "c": int(custodia_fisica), "ol": obs_leg, "id": exp_id}, session=session)

    @staticmethod
    def update_riesgo(exp_id, score_f, rm_score, ac, pc, eb, gf, pt, pa, obs_riesgo, cuota_est, ing_mensuales, moneda, estres_aplicado, dscr, margen_ebitda, tasa_sugerida, covenants, session=None):
        db_action("""UPDATE expedientes_wf SET status_riesgo = 1, score_f = :s, rm_score = :rm,
                     ac = :ac, pc = :pc, eb = :eb, gf = :gf, pt = :pt, pa = :pa, obs_riesgo = :obs, cuota_est = :ce,
                     ing_mensuales = :im, moneda = :mon, estres_aplicado = :ea, dscr = :d,
                     margen_ebitda = :me, tasa_sugerida = :ts, covenants = :cov WHERE id = :id""",
                  {"s": score_f, "rm": rm_score, "ac": ac, "pc": pc, "eb": eb, "gf": gf, "pt": pt, "pa": pa, 
                   "obs": obs_riesgo, "ce": cuota_est, "im": ing_mensuales, "mon": moneda, "ea": int(estres_aplicado), 
                   "d": dscr, "me": margen_ebitda, "ts": tasa_sugerida, "cov": covenants, "id": exp_id}, session=session)

    @staticmethod
    def update_dictamen(exp_id, dictamen, aprobado_por, fecha, tasa=0.0, plazo=36, session=None):
        if dictamen == 'APROBADO':
            db_action("""UPDATE expedientes_wf SET dictamen = 'APROBADO', tasa_aprobada = :t, 
                         aprobado_por = :a, fecha_decision = :f, plan_generado = 1, plazo_meses = :p,
                         estado_workflow = 'APROBADO' WHERE id = :id""", 
                      {"t": tasa, "a": aprobado_por, "f": fecha, "p": plazo, "id": exp_id}, session=session)
        else:
            db_action("""UPDATE expedientes_wf SET dictamen = 'RECHAZADO', aprobado_por = :a,
                         fecha_decision = :f, estado_workflow = 'CERRADO - RECHAZADO' WHERE id = :id""", 
                      {"a": aprobado_por, "f": fecha, "id": exp_id}, session=session)
            
    @staticmethod
    def rechazar_expediente(exp_id, obs, usuario, fecha, session=None):
        """Rechazo definitivo con justificacion registrada."""
        db_action("""UPDATE expedientes_wf SET dictamen = 'RECHAZADO', obs_decision = :o,
                     devuelto_a = '', aprobado_por = :a, fecha_decision = :f WHERE id = :id""",
                  {"o": obs, "a": usuario, "f": fecha, "id": exp_id}, session=session)

    @staticmethod
    def devolver_expediente(exp_id, etapa_destino, observaciones, usuario=None, fecha=None, session=None):
        """
        Devuelve el expediente a una etapa previa.

        Fija el dictamen en 'REVISION-{etapa_destino}' y registra las
        observaciones. `usuario` y `fecha` son opcionales y alimentan la traza
        de auditoria cuando la vista los proporciona.
        """
        db_action("""UPDATE expedientes_wf SET dictamen = :d, devuelto_a = :ar, obs_decision = :o,
                     aprobado_por = :a, fecha_decision = :f WHERE id = :id""",
                  {"d": f"REVISIÓN-{etapa_destino}", "ar": etapa_destino,
                   "o": observaciones, "a": usuario or '', "f": fecha or '', "id": exp_id}, session=session)

    @staticmethod
    def update_estado_cobranza(exp_id, estado, session=None):
        db_action("UPDATE expedientes_wf SET estado_cobranza = :e WHERE id = :id", {"e": estado, "id": exp_id}, session=session)

    @staticmethod
    def clonar_para_reevaluacion(exp_id, fecha, session=None):
        """Expediente nuevo con los datos del indicado y sin firmas; devuelve su id."""
        return _clonar_expediente('expedientes_wf', COLUMNAS_CLONABLES_CORP,
                                  exp_id, fecha, session)

class ExpedienteAutomotrizDAO:
    @staticmethod
    def create(fecha, cliente, cedula, monto, cliente_id=None, descripcion="", session=None):
        db_action("INSERT INTO expedientes_auto (fecha, cliente, cedula, monto, cliente_id, descripcion) VALUES (:f, :c, :r, :m, :cid, :desc)",
                  {"f": fecha, "c": cliente, "r": cedula, "m": monto, "cid": cliente_id, "desc": descripcion}, session=session)

    @staticmethod
    def get_all(session=None):
        """Expedientes automotrices activos como lista de diccionarios."""
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT * FROM expedientes_auto WHERE eliminado = 0"))

    @staticmethod
    def get_by_id(exp_id, session=None):
        if exp_id is None:
            return None
        with sesion_activa(session) as conn:
            query = text("SELECT * FROM expedientes_auto WHERE id = :id AND eliminado = 0")
            row = conn.execute(query, {"id": exp_id}).fetchone()
            if row:
                return dict(row._mapping)
        return None

    @staticmethod
    def count(dictamen: str = None, cliente: str = None,
              status_comp: int = None, status_leg: int = None, status_riesgo: int = None,
              firmas_completas: bool = None, rol_visibilidad: str = None,
              modo_vista: str = None, session=None) -> int:
        filters = {
            'dictamen': dictamen, 
            'cliente': cliente,
            'status_comp': status_comp,
            'status_leg': status_leg,
            'status_riesgo': status_riesgo
        }
        where, params = _build_where(filters, 'expedientes_auto')
        where = _append_firmas(where, firmas_completas)
        where = _append_vista(where, rol_visibilidad, modo_vista, 'expedientes_auto')
        where = _append_activos(where)
        with sesion_activa(session) as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM expedientes_auto{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      dictamen: str = None, cliente: str = None,
                      firmas_completas: bool = None, rol_visibilidad: str = None,
                      modo_vista: str = None, session=None) -> list:
        where, params = _build_where({'dictamen': dictamen, 'cliente': cliente}, 'expedientes_auto')
        where = _append_firmas(where, firmas_completas)
        where = _append_vista(where, rol_visibilidad, modo_vista, 'expedientes_auto')
        where = _append_activos(where)
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM expedientes_auto{where} ORDER BY id ASC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        with sesion_activa(session) as s:
            return _filas(s, text(query), params)

    @staticmethod
    def get_resumen_por_dictamen(session=None) -> dict:
        """
        Conteo y monto agregados por dictamen, resueltos con GROUP BY en el motor.

        Returns:
            dict {dictamen: {'n': int, 'monto': float}} solo con los dictamenes
            presentes; el consumidor debe usar .get() con valores por defecto.
        """
        query = text("""SELECT dictamen, COUNT(*) AS n, SUM(monto) AS monto
                        FROM expedientes_auto WHERE eliminado = 0 GROUP BY dictamen""")
        with sesion_activa(session) as conn:
            filas = conn.execute(query).fetchall()
        return {f[0]: {'n': int(f[1] or 0), 'monto': float(f[2] or 0.0)} for f in filas}

    @staticmethod
    def delete(exp_id, session=None):
        db_action("UPDATE expedientes_auto SET eliminado = 1 WHERE id = :id", {"id": exp_id}, session=session)
        
    @staticmethod
    def update_compliance(exp_id, ocupacion, empleador, telefono, riesgo_aml, origen_fondos, check_pep, check_sanciones, obs, session=None):
        db_action("""UPDATE expedientes_auto SET status_comp = 1, ocupacion = :oc, empleador = :em,
                     telefono = :tel, riesgo_aml = :r, origen_fondos = :o, check_pep = :p,
                     check_sanciones = :s, obs_comp = :ob WHERE id = :id""",
                  {"oc": ocupacion, "em": empleador, "tel": telefono, "r": riesgo_aml, "o": origen_fondos, 
                   "p": int(check_pep), "s": int(check_sanciones), "ob": obs, "id": exp_id}, session=session)

    @staticmethod
    def update_legal(exp_id, marca, modelo, anio, vin, precio_vehiculo, tipo_vehiculo, enganche, plazo_meses, ltv_ratio, seguro_vehiculo, registro_lien, fecha_vencimiento_seguro, obs_leg, vehiculo_placa, seguro_empresa, seguro_poliza, seguro_vigencia, session=None):
        db_action("""UPDATE expedientes_auto SET status_leg = 1, marca = :ma, modelo = :mo, anio = :an,
                     vin = :vi, precio_vehiculo = :pv, tipo_vehiculo = :tv, enganche = :en, plazo_meses = :pl,
                     ltv_ratio = :lt, seguro_vehiculo = :sv, registro_lien = :rl,
                     fecha_vencimiento_seguro = :fvs, obs_leg = :ol,
                     vehiculo_placa = :vp, seguro_empresa = :se, seguro_poliza = :sp,
                     seguro_vigencia = :svg WHERE id = :id""",
                  {"ma": marca, "mo": modelo, "an": anio, "vi": vin, "pv": precio_vehiculo, "tv": tipo_vehiculo, 
                   "en": enganche, "pl": plazo_meses, "lt": ltv_ratio, "sv": int(seguro_vehiculo), "rl": int(registro_lien),
                   "fvs": fecha_vencimiento_seguro, "ol": obs_leg, "vp": vehiculo_placa, "se": seguro_empresa, 
                   "sp": seguro_poliza, "svg": seguro_vigencia, "id": exp_id}, session=session)

    @staticmethod
    def update_riesgo(exp_id, score_f, rm_score, ingreso_mensual, gastos_mensuales, cuota_est, dti_ratio, estabilidad_laboral, estres_aplicado, tasa_sugerida, moneda, obs_riesgo, covenants, session=None):
        db_action("""UPDATE expedientes_auto SET status_riesgo = 1, score_f = :s, rm_score = :rm,
                     ingreso_mensual = :im, gastos_mensuales = :gm, cuota_est = :ce, dti_ratio = :dt,
                     estabilidad_laboral = :el, estres_aplicado = :ea, tasa_sugerida = :ts,
                     moneda = :mon, obs_riesgo = :obs, covenants = :cov WHERE id = :id""",
                  {"s": score_f, "rm": rm_score, "im": ingreso_mensual, "gm": gastos_mensuales, "ce": cuota_est, 
                   "dt": dti_ratio, "el": estabilidad_laboral, "ea": int(estres_aplicado), "ts": tasa_sugerida, 
                   "mon": moneda, "obs": obs_riesgo, "cov": covenants, "id": exp_id}, session=session)

    @staticmethod
    def update_dictamen(exp_id, dictamen, aprobado_por, fecha, tasa=0.0, session=None):
        if dictamen == 'APROBADO':
            db_action("""UPDATE expedientes_auto SET dictamen = 'APROBADO', tasa_aprobada = :t, 
                         aprobado_por = :a, fecha_decision = :f, plan_generado = 1,
                         estado_workflow = 'APROBADO' WHERE id = :id""", 
                      {"t": tasa, "a": aprobado_por, "f": fecha, "id": exp_id}, session=session)
        else:
            db_action("""UPDATE expedientes_auto SET dictamen = 'RECHAZADO', aprobado_por = :a,
                         fecha_decision = :f, estado_workflow = 'CERRADO - RECHAZADO' WHERE id = :id""", 
                      {"a": aprobado_por, "f": fecha, "id": exp_id}, session=session)
            
    @staticmethod
    def rechazar_expediente(exp_id, obs, usuario, fecha, session=None):
        """Rechazo definitivo con justificacion registrada."""
        db_action("""UPDATE expedientes_auto SET dictamen = 'RECHAZADO', obs_decision = :o,
                     devuelto_a = '', aprobado_por = :a, fecha_decision = :f WHERE id = :id""",
                  {"o": obs, "a": usuario, "f": fecha, "id": exp_id}, session=session)

    @staticmethod
    def devolver_expediente(exp_id, etapa_destino, observaciones, usuario=None, fecha=None, session=None):
        """
        Devuelve el expediente a una etapa previa.

        Fija el dictamen en 'REVISION-{etapa_destino}' y registra las
        observaciones. `usuario` y `fecha` son opcionales y alimentan la traza
        de auditoria cuando la vista los proporciona.
        """
        db_action("""UPDATE expedientes_auto SET dictamen = :d, devuelto_a = :ar, obs_decision = :o,
                     aprobado_por = :a, fecha_decision = :f WHERE id = :id""",
                  {"d": f"REVISIÓN-{etapa_destino}", "ar": etapa_destino,
                   "o": observaciones, "a": usuario or '', "f": fecha or '', "id": exp_id}, session=session)

    @staticmethod
    def update_estado_cobranza(exp_id, estado, session=None):
        db_action("UPDATE expedientes_auto SET estado_cobranza = :e WHERE id = :id", {"e": estado, "id": exp_id}, session=session)

    @staticmethod
    def clonar_para_reevaluacion(exp_id, fecha, session=None):
        """Expediente nuevo con los datos del indicado y sin firmas; devuelve su id."""
        return _clonar_expediente('expedientes_auto', COLUMNAS_CLONABLES_AUTO,
                                  exp_id, fecha, session)

# ══ Flujo formal de evaluación ════════════════════════════════════════════
#
# `estado_workflow` es la nomenclatura institucional del expediente y convive
# con `dictamen`, que es el campo heredado por el que se enrutan las bandejas
# (Cumplimiento, Legal, Riesgo, Comité). Ambos se escriben a la vez para que
# el flujo nuevo no deje ciegas a las vistas existentes.
EW_CUMPLIMIENTO = 'EN EVALUACIÓN - CUMPLIMIENTO'
EW_CREDITO_LEGAL = 'EN EVALUACIÓN - CRÉDITO Y LEGAL'
EW_SUBSANACION = 'SUBSANACIÓN COMERCIAL'
EW_RECHAZADO_COMP = 'CERRADO - RECHAZADO CUMPLIMIENTO'

# Etapas que Cumplimiento abre de forma simultánea al certificar
ETAPAS_POST_CUMPLIMIENTO = ('Crédito', 'Legal')

TABLA_POR_TIPO = {'corp': 'expedientes_wf', 'auto': 'expedientes_auto'}


class TareaWorkflowDAO:
    """Tareas abiertas por etapa para un expediente."""

    @staticmethod
    def crear_tareas(exp_id, tipo, etapas, origen='', usuario='', fecha=None,
                     observaciones='', session=None):
        """
        Abre varias tareas de una sola vez, en una única transacción.

        Se usa para que Cumplimiento genere 'Crédito' y 'Legal' de forma
        simultánea: o se crean las dos, o no se crea ninguna.
        """
        etapas = [e for e in (etapas or []) if e]
        if not etapas or exp_id is None:
            return 0
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sesion_activa(session) as conn:
            for etapa in etapas:
                conn.execute(
                    text("""INSERT INTO tareas_workflow
                                (expediente_id, tipo_expediente, etapa, estado,
                                 origen, observaciones, creado_por, fecha_creacion,
                                 fecha_cierre)
                            VALUES (:eid, :tipo, :etapa, 'PENDIENTE', :ori, :obs,
                                    :usr, :fec, '')"""),
                    {"eid": int(exp_id), "tipo": tipo, "etapa": etapa,
                     "ori": origen, "obs": observaciones, "usr": usuario,
                     "fec": fecha})
        return len(etapas)

    @staticmethod
    def get_por_expediente(exp_id, tipo, estado=None, session=None):
        """Tareas del expediente, opcionalmente filtradas por estado."""
        if exp_id is None:
            return []
        cond = " AND estado = :est" if estado else ""
        params = {"eid": int(exp_id), "tipo": tipo}
        if estado:
            params["est"] = estado
        with sesion_activa(session) as conn:
            filas = conn.execute(
                text(f"""SELECT id, expediente_id, tipo_expediente, etapa, estado,
                                origen, observaciones, creado_por, fecha_creacion,
                                fecha_cierre
                         FROM tareas_workflow
                         WHERE expediente_id = :eid AND tipo_expediente = :tipo{cond}
                         ORDER BY id"""), params).fetchall()
        return [dict(f._mapping) for f in filas]

    @staticmethod
    def cerrar_tareas(exp_id, tipo, etapa=None, estado_final='CERRADA', fecha=None, session=None):
        """Cierra las tareas abiertas del expediente (o solo las de una etapa)."""
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = {"eid": int(exp_id), "tipo": tipo, "est": estado_final, "fec": fecha}
        if etapa:
            if etapa in ('Legal', 'Legal Fase 1'):
                cond = " AND etapa IN ('Legal', 'Legal Fase 1')"
            else:
                cond = " AND etapa = :etapa"
                params["etapa"] = etapa
        else:
            cond = ""
        db_action(f"""UPDATE tareas_workflow
                      SET estado = :est, fecha_cierre = :fec
                      WHERE expediente_id = :eid AND tipo_expediente = :tipo
                            AND estado = 'PENDIENTE'{cond}""", params, session=session)

    @staticmethod
    def count_pendientes(etapa=None, session=None):
        """Número de tareas abiertas, opcionalmente de una etapa concreta."""
        params = {}
        if etapa:
            if etapa in ('Legal', 'Legal Fase 1'):
                cond = " AND etapa IN ('Legal', 'Legal Fase 1')"
            else:
                cond = " AND etapa = :etapa"
                params["etapa"] = etapa
        else:
            cond = ""
        with sesion_activa(session) as conn:
            res = conn.execute(
                text(f"SELECT COUNT(*) FROM tareas_workflow "
                     f"WHERE estado = 'PENDIENTE'{cond}"), params).fetchone()
        return res[0] if res else 0


class WorkflowCumplimientoDAO:
    """
    Transiciones de la etapa de Cumplimiento, primera revisión formal.

    Las tres acciones —certificar, observar y rechazar— escriben el estado
    institucional y el dictamen heredado en la misma sentencia, de modo que no
    puede quedar un expediente con ambos campos en desacuerdo.

    Aquí solo queda la escritura: las reglas que deciden **si** una transición
    es legítima viven en `services/workflow_service.py`, que es el único punto
    por el que deben pasar tanto la interfaz como las rutas de la API.
    """

    @staticmethod
    def _tabla(tipo):
        tabla = TABLA_POR_TIPO.get(tipo)
        if not tabla:
            raise ValueError(f"Tipo de expediente no reconocido: {tipo!r}")
        return tabla

    @staticmethod
    def get_estado(exp_id, tipo, session=None):
        """Estado del flujo y firma de Cumplimiento de un expediente."""
        tabla = WorkflowCumplimientoDAO._tabla(tipo)
        with sesion_activa(session) as conn:
            fila = conn.execute(
                text(f"SELECT estado_workflow, dictamen, status_comp "
                     f"FROM {tabla} WHERE id = :id"), {"id": int(exp_id)}).fetchone()
        return dict(fila._mapping) if fila else None

    @staticmethod
    def cumplimiento_certificado(exp_id, tipo, session=None):
        """True si Cumplimiento ya firmó el expediente."""
        estado = WorkflowCumplimientoDAO.get_estado(exp_id, tipo, session=session)
        return bool(estado and estado.get('status_comp') == 1)

    @staticmethod
    def certificar(exp_id, tipo, usuario='', fecha=None, session=None):
        """
        Cierra la etapa de Cumplimiento y abre Crédito y Legal Fase 1.

        Deja el expediente en `EN EVALUACIÓN - CRÉDITO Y LEGAL` y genera las
        dos tareas de forma simultánea.

        Returns:
            int: número de tareas creadas.
        """
        tabla = WorkflowCumplimientoDAO._tabla(tipo)
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db_action(f"""UPDATE {tabla}
                      SET status_comp = 1, estado_workflow = :ew,
                          dictamen = 'PENDIENTE', devuelto_a = ''
                      WHERE id = :id""",
                  {"ew": EW_CREDITO_LEGAL, "id": int(exp_id)}, session=session)

        TareaWorkflowDAO.cerrar_tareas(exp_id, tipo, etapa='Cumplimiento',
                                       estado_final='COMPLETADA', fecha=fecha,
                                       session=session)
        return TareaWorkflowDAO.crear_tareas(
            exp_id, tipo, ETAPAS_POST_CUMPLIMIENTO,
            origen='Cumplimiento', usuario=usuario, fecha=fecha, session=session)

    @staticmethod
    def observar(exp_id, tipo, observaciones, usuario='', fecha=None, session=None):
        """
        Devuelve el expediente al área comercial para subsanación.

        Deja el estado en `SUBSANACIÓN COMERCIAL`, marca el dictamen heredado
        como devuelto a Comercial y abre la tarea comercial correspondiente.
        """
        tabla = WorkflowCumplimientoDAO._tabla(tipo)
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db_action(f"""UPDATE {tabla}
                      SET estado_workflow = :ew, dictamen = 'REVISIÓN-Comercial',
                          devuelto_a = 'Comercial', obs_decision = :obs,
                          aprobado_por = :usr, fecha_decision = :fec
                      WHERE id = :id""",
                  {"ew": EW_SUBSANACION, "obs": observaciones, "usr": usuario,
                   "fec": fecha, "id": int(exp_id)}, session=session)

        TareaWorkflowDAO.cerrar_tareas(exp_id, tipo, estado_final='DEVUELTA',
                                       fecha=fecha, session=session)
        return TareaWorkflowDAO.crear_tareas(
            exp_id, tipo, ('Comercial',), origen='Cumplimiento',
            usuario=usuario, fecha=fecha, observaciones=observaciones,
            session=session)

    @staticmethod
    def rechazar(exp_id, tipo, motivo, usuario='', fecha=None, session=None):
        """
        Desestima el expediente en Cumplimiento y lo archiva.

        Deja el estado en `CERRADO - RECHAZADO CUMPLIMIENTO`, marca el dictamen
        heredado como RECHAZADO —con lo que sale de todas las bandejas— y
        cierra cualquier tarea abierta.
        """
        tabla = WorkflowCumplimientoDAO._tabla(tipo)
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db_action(f"""UPDATE {tabla}
                      SET estado_workflow = :ew, dictamen = 'RECHAZADO',
                          devuelto_a = '', obs_decision = :obs,
                          aprobado_por = :usr, fecha_decision = :fec
                      WHERE id = :id""",
                  {"ew": EW_RECHAZADO_COMP, "obs": motivo, "usr": usuario,
                   "fec": fecha, "id": int(exp_id)}, session=session)

        TareaWorkflowDAO.cerrar_tareas(exp_id, tipo, estado_final='ANULADA',
                                       fecha=fecha, session=session)
        return 0


class ClienteDAO:
    @staticmethod
    def create(fecha_registro, tipo, nombre, cedula_rif, fecha_nacimiento, nacionalidad, telefono, email, direccion, actividad_economica, nombre_rep, cedula_rep, cargo_rep, docs_json, session=None):
        query = """INSERT INTO clientes (fecha_registro,tipo,nombre,cedula_rif,fecha_nacimiento,nacionalidad,
                   telefono,email,direccion,actividad_economica,nombre_rep,cedula_rep,cargo_rep,docs_json,kyc_status) 
                   VALUES (:f,:t,:n,:c,:fn,:nac,:tel,:em,:dir,:act,:nr,:cr,:car,:docs,'Prospecto')"""
        db_action(query, {"f": fecha_registro, "t": tipo, "n": nombre, "c": cedula_rif, "fn": fecha_nacimiento, 
                          "nac": nacionalidad, "tel": telefono, "em": email, "dir": direccion, "act": actividad_economica, 
                          "nr": nombre_rep, "cr": cedula_rep, "car": cargo_rep, "docs": docs_json}, session=session)

    @staticmethod
    def get_all(session=None):
        """Clientes en orden de alta descendente, como lista de diccionarios."""
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT * FROM clientes ORDER BY id DESC"))

    @staticmethod
    def count(nombre: str = None, tipo: str = None, kyc_status: str = None, session=None) -> int:
        where, params = _build_where({'tipo': tipo, 'kyc_status': kyc_status}, 'clientes')
        if nombre:
            connector = ' AND ' if where else ' WHERE '
            where += f"{connector}(nombre LIKE :n OR cedula_rif LIKE :n)"
            params['n'] = f'%{nombre}%'
        with sesion_activa(session) as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM clientes{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 10,
                      nombre: str = None, tipo: str = None,
                      kyc_status: str = None, session=None) -> list:
        where, params = _build_where({'tipo': tipo, 'kyc_status': kyc_status}, 'clientes')
        if nombre:
            connector = ' AND ' if where else ' WHERE '
            where += f"{connector}(nombre LIKE :n OR cedula_rif LIKE :n)"
            params['n'] = f'%{nombre}%'
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM clientes{where} ORDER BY id DESC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        with sesion_activa(session) as s:
            return _filas(s, text(query), params)

    @staticmethod
    def update_docs_and_status(cli_id, docs_json, kyc_status, session=None):
        db_action("UPDATE clientes SET docs_json = :d, kyc_status = :s WHERE id = :id", {"d": docs_json, "s": kyc_status, "id": cli_id}, session=session)

    @staticmethod
    def update_kyc_approval(cli_id, obs_kyc, aprobado_por, kyc_fecha, session=None):
        db_action("""UPDATE clientes SET kyc_status='KYC Aprobado', obs_kyc = :o, kyc_aprobado_por = :a, kyc_fecha = :f WHERE id = :id""",
                  {"o": obs_kyc, "a": aprobado_por, "f": kyc_fecha, "id": cli_id}, session=session)

    @staticmethod
    def update_kyc_status(cli_id, status, session=None):
        db_action("UPDATE clientes SET kyc_status = :s WHERE id = :id", {"s": status, "id": cli_id}, session=session)

    @staticmethod
    def update_kyc_observations(cli_id, obs_kyc, session=None):
        db_action("UPDATE clientes SET obs_kyc = :o WHERE id = :id", {"o": obs_kyc, "id": cli_id}, session=session)

    @staticmethod
    def get_id_by_rif(rif, session=None):
        with sesion_activa(session) as conn:
            query = text("SELECT id FROM clientes WHERE cedula_rif = :r")
            row = conn.execute(query, {"r": rif}).fetchone()
            return row[0] if row else None

    @staticmethod
    def get_by_id(cli_id, session=None):
        if cli_id is None:
            return None
        with sesion_activa(session) as conn:
            query = text("SELECT * FROM clientes WHERE id = :id")
            row = conn.execute(query, {"id": cli_id}).fetchone()
            if row:
                # Retornamos como diccionario para fácil acceso
                return dict(row._mapping)
        return None

# ── Estados de sincronización con SharePoint ─────────────────────────────
SYNC_PENDIENTE     = 'No Sincronizado'
SYNC_DESACTUALIZADO = 'Desactualizado'
SYNC_OK            = 'Sincronizado'


class DocumentoClienteDAO:
    """
    Inventario de los documentos de un cliente y su estado frente a SharePoint.

    El archivo físico lo administra `StorageService`; esta tabla solo registra
    qué archivos existen y si su versión vigente ya viajó a SharePoint.
    """

    @staticmethod
    def get_by_cliente(cliente_id, session=None) -> list:
        """Documentos registrados del cliente, como lista de diccionarios."""
        if cliente_id is None:
            return []
        with sesion_activa(session) as conn:
            filas = conn.execute(
                text("""SELECT id, cliente_id, doc_name, file_name, carpeta,
                               fecha_carga, fecha_sync, sp_sync_status
                        FROM documentos_cliente
                        WHERE cliente_id = :cid
                        ORDER BY file_name"""),
                {"cid": int(cliente_id)}).fetchall()
        return [dict(f._mapping) for f in filas]

    @staticmethod
    def get_sync_status_map(cliente_id, session=None) -> dict:
        """Mapa `{file_name: (id, sp_sync_status)}` para el render de la vista."""
        return {d['file_name']: (d['id'], d['sp_sync_status'])
                for d in DocumentoClienteDAO.get_by_cliente(cliente_id, session=session)}

    @staticmethod
    def get_documento(cliente_id, file_name=None, doc_name=None, session=None):
        """
        Localiza el registro vigente de un documento.

        Se busca por `doc_name` cuando el archivo pertenece a un ítem del
        checklist KYC (su nombre físico cambia si se reemplaza por otro con
        distinta extensión) y por `file_name` en las cargas libres.

        Si la búsqueda por `doc_name` no encuentra nada se reintenta por
        `file_name`: los registros creados por `sincronizar_inventario` nacen sin
        `doc_name`, y sin este reintento una carga posterior del checklist
        duplicaría la fila en lugar de actualizarla.
        """
        if cliente_id is None:
            return None

        criterios = []
        if doc_name:
            criterios.append(("doc_name = :dn", {"dn": str(doc_name)}))
        if file_name:
            criterios.append(("file_name = :fn", {"fn": str(file_name)}))
        if not criterios:
            return None

        with sesion_activa(session) as conn:
            for cond, extra in criterios:
                params = {"cid": int(cliente_id)}
                params.update(extra)
                fila = conn.execute(
                    text(f"""SELECT TOP (1) id, cliente_id, doc_name, file_name, carpeta,
                                    fecha_carga, fecha_sync, sp_sync_status
                             FROM documentos_cliente
                             WHERE cliente_id = :cid AND {cond}
                             ORDER BY id DESC"""), params).fetchone()
                if fila:
                    return dict(fila._mapping)
        return None

    @staticmethod
    def insert_documento(cliente_id, file_name, doc_name='', carpeta='', fecha=None, session=None):
        """
        Alta de un documento nuevo. Nace como `No Sincronizado`.

        Returns:
            int: id del registro creado.
        """
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M")
        with sesion_activa(session) as conn:
            fila = conn.execute(
                text("""INSERT INTO documentos_cliente
                            (cliente_id, doc_name, file_name, carpeta,
                             fecha_carga, fecha_sync, sp_sync_status)
                        OUTPUT INSERTED.id
                        VALUES (:cid, :dn, :fn, :car, :fc, '', :st)"""),
                {"cid": int(cliente_id), "dn": str(doc_name or ''), "fn": str(file_name),
                 "car": str(carpeta or ''), "fc": fecha, "st": SYNC_PENDIENTE}).fetchone()
        return fila[0] if fila else None

    @staticmethod
    def update_documento(doc_id, file_name, carpeta='', fecha=None, doc_name=None, session=None):
        """
        Actualiza un documento existente al reemplazarse su archivo.

        La versión almacenada deja de coincidir con la que hay en SharePoint,
        de modo que el estado pasa a `Desactualizado`. Si se indica `doc_name`
        se aprovecha para vincular al ítem del checklist las filas que se
        crearon desde el inventario sin esa referencia.
        """
        fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M")
        set_doc = ", doc_name = :dn" if doc_name else ""
        params = {"fn": str(file_name), "car": str(carpeta or ''), "fc": fecha,
                  "st": SYNC_DESACTUALIZADO, "id": int(doc_id)}
        if doc_name:
            params["dn"] = str(doc_name)
        db_action(f"""UPDATE documentos_cliente
                      SET file_name = :fn, carpeta = :car, fecha_carga = :fc,
                          sp_sync_status = :st{set_doc}
                      WHERE id = :id""", params, session=session)

    @staticmethod
    def registrar_carga(cliente_id, file_name, doc_name='', carpeta='', session=None):
        """
        Punto único de entrada de las vistas al guardar un archivo.

        Da de alta el documento si es nuevo (`No Sincronizado`) o actualiza el
        registro existente si se trata de un reemplazo (`Desactualizado`).

        Returns:
            tuple(int, str): id del registro y estado resultante.
        """
        existente = DocumentoClienteDAO.get_documento(
            cliente_id, file_name=file_name, doc_name=doc_name, session=session)

        if existente:
            DocumentoClienteDAO.update_documento(existente['id'], file_name, carpeta,
                                                 doc_name=doc_name or None,
                                                 session=session)
            return existente['id'], SYNC_DESACTUALIZADO

        nuevo_id = DocumentoClienteDAO.insert_documento(
            cliente_id, file_name, doc_name, carpeta, session=session)
        return nuevo_id, SYNC_PENDIENTE

    @staticmethod
    def update_sharepoint_sync_status(doc_id, status, session=None):
        """Fija el estado de sincronización de un documento con SharePoint."""
        if doc_id is None:
            return
        db_action("""UPDATE documentos_cliente
                     SET sp_sync_status = :st, fecha_sync = :fs
                     WHERE id = :id""",
                  {"st": str(status),
                   "fs": datetime.now().strftime("%Y-%m-%d %H:%M") if status == SYNC_OK else '',
                   "id": int(doc_id)}, session=session)

    @staticmethod
    def sincronizar_inventario(cliente_id, file_names, carpeta='', session=None):
        """
        Registra los archivos que ya existen en el repositorio pero aún no
        tienen fila en la tabla (clientes anteriores a esta funcionalidad).

        Returns:
            int: número de registros creados.
        """
        if cliente_id is None or not file_names:
            return 0

        conocidos = {d['file_name'] for d in DocumentoClienteDAO.get_by_cliente(cliente_id, session=session)}
        creados = 0
        for nombre in file_names:
            if nombre in conocidos:
                continue
            DocumentoClienteDAO.insert_documento(cliente_id, nombre, '', carpeta, session=session)
            creados += 1
        return creados


def get_exposicion_por_cliente(top_n: int = 10, session=None) -> list:
    """
    Exposición aprobada por cliente, consolidando cartera corporativa y
    automotriz. La unión, la suma y el orden se resuelven en el motor;
    `top_n` limita las filas devueltas con TOP.

    Returns:
        list[dict] con las claves 'cliente' y 'monto', de mayor a menor.
    """
    query = text(f"""
        SELECT TOP (:top_n) cliente, SUM(monto) AS monto
        FROM (
            SELECT cliente, monto FROM expedientes_wf
            WHERE dictamen = 'APROBADO' AND eliminado = 0
            UNION ALL
            SELECT cliente, monto FROM expedientes_auto
            WHERE dictamen = 'APROBADO' AND eliminado = 0
        ) AS carteras
        GROUP BY cliente
        ORDER BY SUM(monto) DESC""")
    with sesion_activa(session) as conn:
        filas = conn.execute(query, {"top_n": int(top_n)}).fetchall()
    return [{'cliente': f[0], 'monto': float(f[1] or 0.0)} for f in filas]


def get_estados_cobranza_consolidado(session=None) -> dict:
    """
    Conteo de créditos aprobados por estado de cobranza, uniendo ambas carteras.
    Sustituye la alineación de Series `value_counts().add(..., fill_value=0)`.
    """
    query = text("""
        SELECT estado_cobranza, COUNT(*) AS n
        FROM (
            SELECT estado_cobranza FROM expedientes_wf
            WHERE dictamen = 'APROBADO' AND eliminado = 0
            UNION ALL
            SELECT estado_cobranza FROM expedientes_auto
            WHERE dictamen = 'APROBADO' AND eliminado = 0
        ) AS carteras
        GROUP BY estado_cobranza""")
    with sesion_activa(session) as conn:
        filas = conn.execute(query).fetchall()
    return {(f[0] or 'Al día'): int(f[1] or 0) for f in filas}


class PlanPagoDAO:
    @staticmethod
    def delete_by_expediente(exp_id, tipo, session=None):
        db_action("DELETE FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t", {"id": exp_id, "t": tipo}, session=session)
        
    @staticmethod
    def insert_many(rows, session=None):
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
            
        with sesion_activa(session) as conn:
            conn.execute(query, formatted_rows)

    @staticmethod
    def get_by_expediente(exp_id, tipo, session=None):
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT * FROM plan_pagos WHERE expediente_id = :id "
                                  "AND tipo_expediente = :t ORDER BY periodo"),
                          {"id": exp_id, "t": tipo})

    @staticmethod
    def get_by_expediente_tabla(exp_id, tipo, session=None):
        """Cuotas con los encabezados de presentacion ya aplicados."""
        query = text("SELECT periodo AS [N°], fecha_pago AS [Fecha], cuota AS [Cuota], capital AS [Capital], interes AS [Interés], saldo AS [Saldo] FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t ORDER BY periodo")
        with sesion_activa(session) as s:
            return _filas(s, query, {"id": exp_id, "t": tipo})

    @staticmethod
    def mark_as_paid(plan_id, session=None):
        db_action("UPDATE plan_pagos SET estado='PAGADO' WHERE id = :id", {"id": plan_id}, session=session)
        
    @staticmethod
    def get_all(session=None):
        """Todas las cuotas ordenadas por fecha, como lista de diccionarios."""
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT * FROM plan_pagos ORDER BY fecha_pago"))

    @staticmethod
    def count(expediente_id: int = None, tipo: str = None, estado: str = None, session=None) -> int:
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo, 'estado': estado},
            'plan_pagos')
        with sesion_activa(session) as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM plan_pagos{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 15,
                      expediente_id: int = None, tipo: str = None,
                      estado: str = None, session=None) -> list:
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo, 'estado': estado},
            'plan_pagos')
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM plan_pagos{where} ORDER BY fecha_pago OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        with sesion_activa(session) as s:
            return _filas(s, text(query), params)

    @staticmethod
    def get_resumen_por_estado(session=None) -> dict:
        """
        SUM(cuota) y COUNT(*) agrupados por estado del plan de pagos.

        Returns:
            dict {estado: {'n': int, 'monto': float}}
        """
        query = text("""SELECT estado, COUNT(*) AS n, SUM(cuota) AS monto
                        FROM plan_pagos GROUP BY estado""")
        with sesion_activa(session) as conn:
            filas = conn.execute(query).fetchall()
        return {f[0]: {'n': int(f[1] or 0), 'monto': float(f[2] or 0.0)} for f in filas}

    @staticmethod
    def get_resumen_vencimientos(fecha_referencia: str, dias_proximos: int = 30, session=None) -> dict:
        """
        Agregación condicional en una sola pasada: cuotas vencidas y cuotas que
        vencen dentro de la ventana indicada.

        Returns:
            dict con 'n_vencidas', 'monto_vencido', 'n_proximas', 'monto_proximo'.
        """
        from datetime import datetime, timedelta
        base = datetime.strptime(fecha_referencia[:10], "%Y-%m-%d").date()
        hasta = (base + timedelta(days=int(dias_proximos))).strftime("%Y-%m-%d")

        query = text("""
            SELECT
              SUM(CASE WHEN estado = 'PENDIENTE' AND fecha_pago < :hoy THEN 1 ELSE 0 END) AS n_venc,
              SUM(CASE WHEN estado = 'PENDIENTE' AND fecha_pago < :hoy THEN cuota ELSE 0 END) AS m_venc,
              SUM(CASE WHEN estado = 'PENDIENTE' AND fecha_pago >= :hoy
                        AND fecha_pago <= :hasta THEN 1 ELSE 0 END) AS n_prox,
              SUM(CASE WHEN estado = 'PENDIENTE' AND fecha_pago >= :hoy
                        AND fecha_pago <= :hasta THEN cuota ELSE 0 END) AS m_prox
            FROM plan_pagos
            WHERE (
                (tipo_expediente = 'corp' AND EXISTS (
                    SELECT 1 FROM expedientes_wf w WHERE w.id = plan_pagos.expediente_id AND w.eliminado = 0 AND w.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                ))
                OR
                (tipo_expediente = 'auto' AND EXISTS (
                    SELECT 1 FROM expedientes_auto a WHERE a.id = plan_pagos.expediente_id AND a.eliminado = 0 AND a.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                ))
            )""")
        with sesion_activa(session) as conn:
            f = conn.execute(query, {"hoy": fecha_referencia, "hasta": hasta}).fetchone()
        if not f:
            return {'n_vencidas': 0, 'monto_vencido': 0.0, 'n_proximas': 0, 'monto_proximo': 0.0}
        return {'n_vencidas': int(f[0] or 0), 'monto_vencido': float(f[1] or 0.0),
                'n_proximas': int(f[2] or 0), 'monto_proximo': float(f[3] or 0.0)}

    @staticmethod
    def get_aging_buckets(fecha_referencia: str, session=None) -> dict:
        """
        Tramos de antigüedad de deuda calculados íntegramente en el motor con
        DATEDIFF y CASE WHEN. Devuelve siempre los cuatro tramos, con ceros en
        los que no tienen cuotas.
        """
        tramos = ["1-30 días", "31-60 días", "61-90 días", "> 90 días"]
        resultado = {t: {'n': 0, 'monto': 0.0, 'prom_dias': 0.0} for t in tramos}

        query = text("""
            SELECT tramo, COUNT(*) AS n, SUM(cuota) AS monto,
                   AVG(CAST(dias AS FLOAT)) AS prom_dias
            FROM (
                SELECT cuota,
                       DATEDIFF(day, CONVERT(date, fecha_pago, 23), CAST(:hoy AS date)) AS dias,
                       CASE
                         WHEN DATEDIFF(day, CONVERT(date, fecha_pago, 23), CAST(:hoy AS date))
                              BETWEEN 1 AND 30 THEN N'1-30 días'
                         WHEN DATEDIFF(day, CONVERT(date, fecha_pago, 23), CAST(:hoy AS date))
                              BETWEEN 31 AND 60 THEN N'31-60 días'
                         WHEN DATEDIFF(day, CONVERT(date, fecha_pago, 23), CAST(:hoy AS date))
                              BETWEEN 61 AND 90 THEN N'61-90 días'
                         WHEN DATEDIFF(day, CONVERT(date, fecha_pago, 23), CAST(:hoy AS date))
                              > 90 THEN N'> 90 días'
                         ELSE NULL
                       END AS tramo
                FROM plan_pagos
                WHERE estado = 'PENDIENTE' AND fecha_pago < :hoy
                  AND (
                      (tipo_expediente = 'corp' AND EXISTS (
                          SELECT 1 FROM expedientes_wf w WHERE w.id = plan_pagos.expediente_id AND w.eliminado = 0 AND w.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                      ))
                      OR
                      (tipo_expediente = 'auto' AND EXISTS (
                          SELECT 1 FROM expedientes_auto a WHERE a.id = plan_pagos.expediente_id AND a.eliminado = 0 AND a.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                      ))
                  )
            ) AS t
            WHERE tramo IS NOT NULL
            GROUP BY tramo""")
        with sesion_activa(session) as conn:
            filas = conn.execute(query, {"hoy": fecha_referencia}).fetchall()

        for f in filas:
            if f[0] in resultado:
                resultado[f[0]] = {'n': int(f[1] or 0), 'monto': float(f[2] or 0.0),
                                   'prom_dias': float(f[3] or 0.0)}
        return resultado

    @staticmethod
    def get_vencidos_detalle(fecha_referencia: str, session=None) -> list:
        """
        Cuotas vencidas con los días de atraso ya calculados por el motor,
        listas para la tabla de detalle. Evita el parseo de fechas en memoria.
        """
        query = text("""
            SELECT expediente_id, tipo_expediente, periodo, fecha_pago, cuota,
                   DATEDIFF(day, CONVERT(date, fecha_pago, 23), CAST(:hoy AS date)) AS dias_atraso
            FROM plan_pagos
            WHERE estado = 'PENDIENTE' AND fecha_pago < :hoy
              AND (
                  (tipo_expediente = 'corp' AND EXISTS (
                      SELECT 1 FROM expedientes_wf w WHERE w.id = plan_pagos.expediente_id AND w.eliminado = 0 AND w.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                  ))
                  OR
                  (tipo_expediente = 'auto' AND EXISTS (
                      SELECT 1 FROM expedientes_auto a WHERE a.id = plan_pagos.expediente_id AND a.eliminado = 0 AND a.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                  ))
              )
            ORDER BY fecha_pago ASC""")
        with sesion_activa(session) as s:
            return _filas(s, query, {"hoy": fecha_referencia})

    @staticmethod
    def get_flujo_mensual(fecha_desde: str, fecha_hasta: str, session=None) -> list:
        """
        Cobros pendientes proyectados, agrupados por mes con LEFT(fecha_pago, 7).

        Returns:
            list[dict] con 'mes' y 'monto', ordenados cronológicamente.
        """
        query = text("""
            SELECT LEFT(fecha_pago, 7) AS mes, SUM(cuota) AS monto
            FROM plan_pagos
            WHERE estado = 'PENDIENTE' AND fecha_pago >= :desde AND fecha_pago <= :hasta
            GROUP BY LEFT(fecha_pago, 7)
            ORDER BY LEFT(fecha_pago, 7)""")
        with sesion_activa(session) as conn:
            filas = conn.execute(query, {"desde": fecha_desde, "hasta": fecha_hasta}).fetchall()
        return [{'mes': f[0], 'monto': float(f[1] or 0.0)} for f in filas]

    @staticmethod
    def count_vencidos(fecha_referencia: str, session=None) -> int:
        query = text("SELECT COUNT(*) FROM plan_pagos WHERE estado = 'PENDIENTE' AND fecha_pago < :f")
        with sesion_activa(session) as conn:
            res = conn.execute(query, {"f": fecha_referencia}).fetchone()
            return res[0] if res else 0

class GestionCobranzaDAO:
    @staticmethod
    def create(exp_id, tipo, fecha, tipo_gestion, responsable, resultado, prox_accion, fecha_prox, obs, session=None):
        db_action("""INSERT INTO gestiones_cobranza (expediente_id, tipo_expediente, fecha, tipo_gestion, 
                     responsable, resultado, proxima_accion, fecha_proxima, obs) 
                     VALUES (:id, :t, :f, :tg, :res, :resu, :pa, :fp, :o)""",
                  {"id": exp_id, "t": tipo, "f": fecha, "tg": tipo_gestion, "res": responsable, 
                   "resu": resultado, "pa": prox_accion, "fp": fecha_prox, "o": obs}, session=session)

    @staticmethod
    def get_all(session=None):
        """Gestiones de cobro, de la mas reciente a la mas antigua."""
        with sesion_activa(session) as s:
            return _filas(s, text("SELECT * FROM gestiones_cobranza ORDER BY fecha DESC"))

    @staticmethod
    def count(expediente_id: int = None, tipo: str = None, session=None) -> int:
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo}, 'gestiones_cobranza')
        with sesion_activa(session) as conn:
            res = conn.execute(text(f"SELECT COUNT(*) FROM gestiones_cobranza{where}"), params).fetchone()
            return res[0] if res else 0

    @staticmethod
    def get_paginated(page: int = 1, page_size: int = 15,
                      expediente_id: int = None, tipo: str = None, session=None) -> list:
        where, params = _build_where(
            {'expediente_id': expediente_id, 'tipo_expediente': tipo}, 'gestiones_cobranza')
        offset = (page - 1) * page_size
        params['off'] = offset
        params['lim'] = page_size
        query = f"SELECT * FROM gestiones_cobranza{where} ORDER BY fecha DESC OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
        with sesion_activa(session) as s:
            return _filas(s, text(query), params)
class PagoRecibidoDAO:
    @staticmethod
    def create(exp_id, tipo, fecha_pago, monto, referencia, session=None):
        db_action("""INSERT INTO pagos_recibidos (expediente_id, tipo_expediente, fecha_pago, monto, referencia) 
                     VALUES (:id, :t, :f, :m, :r)""",
                  {"id": exp_id, "t": tipo, "f": fecha_pago, "m": monto, "r": referencia}, session=session)


# ── Evaluaciones de Riesgo ────────────────────────────────────────────
# Columnas persistidas de cada formulario. Son constantes del módulo, nunca
# datos del llamador: por eso pueden componerse en el SQL, mientras que los
# valores viajan siempre como parámetros nombrados.
COLUMNAS_EVAL_RIESGO_CORP = (
    'activos_corrientes', 'pasivos_corrientes', 'pasivos_totales', 'patrimonio',
    'activos_totales', 'caja_equivalentes', 'cuentas_por_cobrar',
    'cuentas_por_pagar', 'inventarios', 'deuda_financiera_total',
    'utilidades_retenidas', 'valor_patrimonio_mercado',
    'ebitda', 'gastos_financieros', 'depreciacion_amortizacion', 'costo_ventas',
    'impuestos_estimados', 'utilidad_neta',
    'ingresos_mensuales', 'cuota_mensual', 'aplicar_estres', 'kc_score',
    'monto_credito', 'tasa_interes_anual', 'plazo_meses', 'meses_gracia',
    'moneda', 'covenants', 'obs_riesgo', 'entradas_ihp_json',
)

COLUMNAS_EVAL_RIESGO_AUTO = (
    'ingreso_mensual', 'gastos_fijos', 'cuota_mensual', 'ltv_ratio',
    'estabilidad_laboral', 'aplicar_estres', 'kc_score',
    'moneda', 'covenants', 'obs_riesgo',
)


def _upsert_evaluacion(tabla, columnas, expediente_id, datos, usuario, fecha, session):
    """
    Inserta o actualiza la evaluación de un expediente con un único `MERGE`.

    `HOLDLOCK` serializa el MERGE sobre la clave: sin él, dos guardados
    simultáneos del mismo expediente pueden no ver la fila y chocar con la
    restricción UNIQUE al insertar los dos.

    `datos` debe traer todas las columnas: el guardado reemplaza el formulario
    entero, y una ausente produce `KeyError` en lugar de dejar un valor viejo
    mezclado con los nuevos. El esquema Pydantic de la ruta ya las garantiza.
    """
    todas = (*columnas, 'actualizado_por', 'fecha_actualizacion')
    params = {col: datos[col] for col in columnas}
    params.update({'expediente_id': expediente_id,
                   'actualizado_por': usuario or '', 'fecha_actualizacion': fecha})

    origen = ', '.join(f':{col} AS {col}' for col in ('expediente_id', *todas))
    asignaciones = ', '.join(f'{col} = origen.{col}' for col in todas)
    insertar = ', '.join(('expediente_id', *todas))
    valores = ', '.join(f'origen.{col}' for col in ('expediente_id', *todas))

    consulta = f"""
    MERGE {tabla} WITH (HOLDLOCK) AS destino
    USING (SELECT {origen}) AS origen
    ON destino.expediente_id = origen.expediente_id
    WHEN MATCHED THEN UPDATE SET {asignaciones}
    WHEN NOT MATCHED THEN INSERT ({insertar}) VALUES ({valores});
    """
    db_action(consulta, params, session=session)


def _evaluacion_por_expediente(tabla, expediente_id, session):
    with sesion_activa(session) as s:
        filas = _filas(s, text(f"SELECT * FROM {tabla} WHERE expediente_id = :id"),
                       {'id': expediente_id})
    return filas[0] if filas else None


class EvaluacionRiesgoCorpDAO:
    """Formulario de Riesgo corporativo guardado, uno por expediente de `expedientes_wf`."""

    COLUMNAS = COLUMNAS_EVAL_RIESGO_CORP

    @staticmethod
    def upsert(expediente_id, datos, usuario='', fecha='', session=None):
        _upsert_evaluacion('evaluaciones_riesgo_corp', COLUMNAS_EVAL_RIESGO_CORP,
                           expediente_id, datos, usuario, fecha, session)

    @staticmethod
    def get_by_expediente(expediente_id, session=None):
        """Evaluación guardada como diccionario, o `None` si aún no hay ninguna."""
        return _evaluacion_por_expediente('evaluaciones_riesgo_corp', expediente_id, session)


class EvaluacionRiesgoAutoDAO:
    """Formulario de Riesgo automotriz guardado, uno por expediente de `expedientes_auto`."""

    COLUMNAS = COLUMNAS_EVAL_RIESGO_AUTO

    @staticmethod
    def upsert(expediente_id, datos, usuario='', fecha='', session=None):
        _upsert_evaluacion('evaluaciones_riesgo_auto', COLUMNAS_EVAL_RIESGO_AUTO,
                           expediente_id, datos, usuario, fecha, session)

    @staticmethod
    def get_by_expediente(expediente_id, session=None):
        """Evaluación guardada como diccionario, o `None` si aún no hay ninguna."""
        return _evaluacion_por_expediente('evaluaciones_riesgo_auto', expediente_id, session)


class MetricasDashboardDAO:
    """
    Agregados del tablero, resueltos con COUNT en el motor.

    Las dos lineas de producto viven en tablas distintas pero con las mismas
    columnas de circuito, asi que cada metrica se calcula con la misma condicion
    sobre ambas y se suma. Nada se trae a memoria: son conteos, no listados.

    **Atribucion de las paradas.** El esquema no guarda quien detuvo un
    expediente: guarda como quedo. De ahi se deduce la etapa responsable:

    * `estado_workflow = 'CERRADO - RECHAZADO CUMPLIMIENTO'` es el rechazo
      explicito de Cumplimiento, y la devolucion a 'Comercial' es su
      subsanacion; las dos son paradas suyas.
    * Una devolucion a 'Credito' devuelve el expediente a Riesgo, y una a
      'Legal' a Legal: el destino nombra la etapa que tiene que rehacer su
      trabajo.
    * Un rechazo firme tras la firma de Cumplimiento se atribuye a la etapa que
      no llego a firmar.

    Un expediente parado que no encaje en ninguno de los tres casos —un rechazo
    del Comite con las tres firmas puestas, por ejemplo— no se cuenta en
    ninguna: la suma de las tres no tiene por que ser el total de paradas.
    """

    # Parado: rechazado o devuelto, con cualquiera de las dos nomenclaturas.
    PARADO = ("(dictamen IN ('RECHAZADO', 'DENEGADO', 'FRENADO', 'DEVUELTO')"
              " OR dictamen LIKE 'REVISI%')")

    LISTO_COMITE = ("dictamen = 'PENDIENTE' AND status_comp = 1"
                    " AND status_leg = 1 AND status_riesgo = 1")

    FRENADO_CUMPLIMIENTO = (
        "estado_workflow = 'CERRADO - RECHAZADO CUMPLIMIENTO'"
        " OR devuelto_a LIKE 'Comercial%'"
        " OR devuelto_a LIKE 'Cumplimiento%'"
        " OR (status_comp = 0 AND dictamen IN ('RECHAZADO', 'DENEGADO'))")

    FRENADO_RIESGO = (
        "status_comp = 1 AND ("
        "devuelto_a LIKE 'Cr%dito%'"
        " OR (dictamen IN ('RECHAZADO', 'DENEGADO')"
        "     AND status_riesgo = 0 AND status_leg = 1))")

    FRENADO_LEGAL = (
        "status_comp = 1 AND ("
        "devuelto_a LIKE 'Legal%'"
        " OR (dictamen IN ('RECHAZADO', 'DENEGADO')"
        "     AND status_leg = 0 AND status_riesgo = 1))")

    @staticmethod
    def _contar(condicion, session=None):
        """Suma el conteo de la condicion en las dos lineas de producto."""
        consulta = text(
            "SELECT (SELECT COUNT(*) FROM expedientes_wf WHERE eliminado = 0"
            f" AND ({condicion}))"
            " + (SELECT COUNT(*) FROM expedientes_auto WHERE eliminado = 0"
            f" AND ({condicion}))")
        with sesion_activa(session) as s:
            return int(s.execute(consulta).scalar() or 0)

    @staticmethod
    def _contar_tabla(tabla, condicion='1 = 1', session=None):
        consulta = text(f"SELECT COUNT(*) FROM {tabla} WHERE eliminado = 0"
                        f" AND ({condicion})")
        with sesion_activa(session) as s:
            return int(s.execute(consulta).scalar() or 0)

    @staticmethod
    def resumen(session=None):
        """Las ocho metricas del tablero, en un diccionario plano."""
        contar = MetricasDashboardDAO._contar
        parado = MetricasDashboardDAO.PARADO

        with sesion_activa(session) as s:
            clientes = int(s.execute(
                text("SELECT COUNT(*) FROM clientes")).scalar() or 0)

        corporativos = MetricasDashboardDAO._contar_tabla(
            'expedientes_wf', session=session)
        automotrices = MetricasDashboardDAO._contar_tabla(
            'expedientes_auto', session=session)

        return {
            "clientes": clientes,
            "creditos_total": corporativos + automotrices,
            "creditos_corporativos": corporativos,
            "creditos_automotrices": automotrices,
            "listos_comite": contar(MetricasDashboardDAO.LISTO_COMITE, session),
            "frenados_cumplimiento": contar(
                f"{parado} AND ({MetricasDashboardDAO.FRENADO_CUMPLIMIENTO})", session),
            "frenados_riesgo": contar(
                f"{parado} AND ({MetricasDashboardDAO.FRENADO_RIESGO})", session),
            "frenados_legal": contar(
                f"{parado} AND ({MetricasDashboardDAO.FRENADO_LEGAL})", session),
        }


class DocumentoExpedienteDAO:
    """
    Documentos cargados contra una solicitud de credito.

    Son los papeles de la operacion —estados financieros del ejercicio, el
    avaluo de la garantia, la factura del bien a prendar— y no los del padron:
    el archivo fisico lo administra `StorageService` en la carpeta del cliente,
    y esta tabla registra a que expediente pertenece cada uno.

    La baja es logica: Legal pudo haber consultado un documento, asi que su
    rastro se conserva aunque deje de ofrecerse para descarga.
    """

    @staticmethod
    def create(expediente_id, tipo, file_name, carpeta, tamano_bytes,
               cargado_por, fecha, session=None):
        db_action("""INSERT INTO documentos_expediente
                     (expediente_id, tipo_expediente, file_name, carpeta,
                      tamano_bytes, cargado_por, fecha_carga)
                     VALUES (:id, :t, :fn, :c, :tam, :por, :fecha)""",
                  {"id": int(expediente_id), "t": tipo, "fn": file_name,
                   "c": carpeta, "tam": int(tamano_bytes or 0),
                   "por": cargado_por or "", "fecha": fecha or ""},
                  session=session)

    @staticmethod
    def get_by_expediente(expediente_id, tipo, session=None) -> list:
        """Documentos vigentes del expediente, del mas reciente al mas antiguo."""
        if expediente_id is None:
            return []
        with sesion_activa(session) as s:
            return _filas(s, text(
                """SELECT id, expediente_id, tipo_expediente, file_name, carpeta,
                          tamano_bytes, cargado_por, fecha_carga,
                          sp_sync_status, fecha_sync
                   FROM documentos_expediente
                   WHERE expediente_id = :id AND tipo_expediente = :t
                     AND eliminado = 0
                   ORDER BY id DESC"""),
                {"id": int(expediente_id), "t": tipo})

    @staticmethod
    def get_documento(doc_id, session=None):
        """Un documento por su id, o None si no existe o esta dado de baja."""
        with sesion_activa(session) as s:
            filas = _filas(s, text(
                """SELECT id, expediente_id, tipo_expediente, file_name, carpeta,
                          tamano_bytes, cargado_por, fecha_carga,
                          sp_sync_status, fecha_sync
                   FROM documentos_expediente
                   WHERE id = :id AND eliminado = 0"""), {"id": int(doc_id)})
        return filas[0] if filas else None

    @staticmethod
    def delete(doc_id, session=None):
        db_action("UPDATE documentos_expediente SET eliminado = 1 WHERE id = :id",
                  {"id": int(doc_id)}, session=session)

    @staticmethod
    def update_sync_status(doc_id, estado, fecha='', session=None):
        """Fija el estado frente a SharePoint y la fecha del ultimo envio."""
        db_action("""UPDATE documentos_expediente
                     SET sp_sync_status = :st, fecha_sync = :fs
                     WHERE id = :id""",
                  {"st": estado, "fs": fecha or '', "id": int(doc_id)},
                  session=session)
