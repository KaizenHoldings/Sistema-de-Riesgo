import os
import urllib.parse
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from services.security_service import SecurityService

load_dotenv()

# ── Configuración de SQL Server ──────────────────────────────────────────────
RAW_DB_URL = os.getenv("DATABASE_URL", "")


def get_sqlalchemy_url(url, override_db=None):
    """Convierte la URL de configuración a un formato aceptado por SQLAlchemy."""
    if not url.startswith("sqlserver://"):
        return url

    try:
        clean_url = url.replace("sqlserver://", "")
        parts = clean_url.split(";")
        server_port = parts[0]
        params = {p.split("=")[0].lower(): p.split("=")[1] for p in parts[1:] if "=" in p}

        server = server_port.split(":")[0]
        port = server_port.split(":")[1] if ":" in server_port else "1433"

        # Resolución dinámica del driver ODBC (ODBC Driver 18 o 17 según disponibilidad en el SO)
        driver_env = os.getenv("SQL_DRIVER", "").strip()
        if driver_env:
            driver = driver_env if driver_env.startswith("{") and driver_env.endswith("}") else f"{{{driver_env}}}"
        else:
            driver = "{ODBC Driver 18 for SQL Server}"
            try:
                import pyodbc
                available = pyodbc.drivers()
                for cand in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]:
                    if cand in available:
                        driver = f"{{{cand}}}"
                        break
            except Exception:
                pass

        db = override_db or params.get("database", "kfg_ecosystem")
        uid = params.get("user", "")
        pwd = params.get("password", "")
        encrypt = "yes" if params.get("encrypt", "true").lower() == "true" else "no"
        trust = "yes" if params.get("trustservercertificate", "true").lower() == "true" else "no"

        # Construimos la cadena ODBC
        odbc_str = f"DRIVER={driver};SERVER={server},{port};DATABASE={db};UID={uid};PWD={pwd};Encrypt={encrypt};TrustServerCertificate={trust};"

        # Retornamos formateado para SQLAlchemy
        quoted_odbc = urllib.parse.quote_plus(odbc_str)
        return f"mssql+pyodbc:///?odbc_connect={quoted_odbc}"
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        return url


def ensure_database_exists():
    """
    Si el contenedor de SQL Server arranca de cero, la base 'kfg_ecosystem' no existe aún.
    Esta función se conecta a 'master' y ejecuta CREATE DATABASE antes del init_db.
    """
    if not RAW_DB_URL or not RAW_DB_URL.startswith("sqlserver://"):
        return
    try:
        clean_url = RAW_DB_URL.replace("sqlserver://", "")
        parts = clean_url.split(";")
        params = {p.split("=")[0].lower(): p.split("=")[1] for p in parts[1:] if "=" in p}
        target_db = params.get("database", "kfg_ecosystem")

        # Conectar a master con autocommit
        master_uri = get_sqlalchemy_url(RAW_DB_URL, override_db="master")
        master_engine = create_engine(master_uri, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
        with master_engine.connect() as conn:
            check_q = text("SELECT 1 FROM sys.databases WHERE name = :name")
            if not conn.execute(check_q, {"name": target_db}).fetchone():
                print(f"[SQL Server] Creando base de datos inicial [{target_db}]...")
                conn.execute(text(f"CREATE DATABASE [{target_db}]"))
                print(f"[SQL Server] Base de datos [{target_db}] creada exitosamente.")
        master_engine.dispose()
    except Exception as e:
        print(f"[SQL Server] Aviso en ensure_database_exists: {e}")


# Inicialización del Engine global
DATABASE_URI = get_sqlalchemy_url(RAW_DB_URL)
engine = create_engine(DATABASE_URI, pool_pre_ping=True)

# Fábrica de sesiones ligada al engine global.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_connection():
    """Retorna una conexión compatible con Pandas (Engine o Connection)."""
    return engine


def get_db():
    """Dependencia de sesión para `Depends(get_db)` en FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def sesion_activa(session=None):
    """
    Sesión de trabajo para DAOs:
    Reutiliza la sesión si se recibe; de lo contrario abre una atómica con commit/rollback.
    """
    if session is not None:
        yield session
        return

    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def db_action(query, params=()):
    """Ejecuta una consulta SQL genérica que requiere commit."""
    with sesion_activa() as s:
        s.execute(text(query), params or {})


def init_db():
    """Inicializa la base de datos en SQL Server usando SQLAlchemy."""
    # 1. Asegurar que la base de datos exista en el servidor SQL Server
    ensure_database_exists()

    # 2. Crear tablas y registros por defecto dentro de la base de datos
    with engine.begin() as conn:
        def table_exists(name):
            q = text("SELECT 1 FROM sys.tables WHERE name = :name")
            return conn.execute(q, {"name": name}).fetchone() is not None

        def column_exists(t_name, c_name):
            q = text("SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(:t) AND name = :c")
            return conn.execute(q, {"t": t_name, "c": c_name}).fetchone() is not None

        # ── Expedientes Corporativos ──────────────────────────────
        if not table_exists('expedientes_wf'):
            conn.execute(text('''CREATE TABLE expedientes_wf (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fecha NVARCHAR(50), cliente NVARCHAR(255), rif NVARCHAR(50), monto FLOAT,
                status_comp INT DEFAULT 0, riesgo_aml NVARCHAR(50) DEFAULT 'Bajo',
                origen_fondos NVARCHAR(MAX) DEFAULT '', obs_comp NVARCHAR(MAX) DEFAULT '',
                status_leg INT DEFAULT 0, v_garantia FLOAT DEFAULT 0, obs_leg NVARCHAR(MAX) DEFAULT '',
                status_riesgo INT DEFAULT 0, score_f FLOAT DEFAULT 0,
                rm_score FLOAT DEFAULT 0, obs_riesgo NVARCHAR(MAX) DEFAULT '',
                ac FLOAT DEFAULT 0, pc FLOAT DEFAULT 1, eb FLOAT DEFAULT 0, gf FLOAT DEFAULT 1,
                pt FLOAT DEFAULT 0, pa FLOAT DEFAULT 1,
                dictamen NVARCHAR(50) DEFAULT 'PENDIENTE',
                garantias_json NVARCHAR(MAX) DEFAULT '[]', custodia_fisica INT DEFAULT 0,
                fecha_vencimiento_garantia NVARCHAR(50), ltv_ratio FLOAT DEFAULT 0,
                eliminado BIT NOT NULL DEFAULT 0)'''))

        # Columnas incrementales expedientes_wf
        columns_wf = [
            ("cuota_est", "FLOAT DEFAULT 0"), ("ing_mensuales", "FLOAT DEFAULT 0"),
            ("moneda", "NVARCHAR(10) DEFAULT 'USD'"), ("estres_aplicado", "INT DEFAULT 0"),
            ("dscr", "FLOAT DEFAULT 0"), ("margen_ebitda", "FLOAT DEFAULT 0"),
            ("check_pep", "INT DEFAULT 0"), ("check_sanciones", "INT DEFAULT 0"),
            ("tasa_sugerida", "FLOAT DEFAULT 0"), ("tasa_aprobada", "FLOAT DEFAULT 0"),
            ("aprobado_por", "NVARCHAR(255) DEFAULT ''"), ("fecha_decision", "NVARCHAR(50) DEFAULT ''"),
            ("covenants", "NVARCHAR(MAX) DEFAULT ''"), ("plazo_meses", "INT DEFAULT 36"),
            ("cliente_id", "INT DEFAULT NULL"), ("plan_generado", "INT DEFAULT 0"),
            ("estado_cobranza", "NVARCHAR(50) DEFAULT 'Al día'"), ("tipo_producto", "NVARCHAR(50) DEFAULT 'Corporativo'"),
            ("ingresos_mensuales", "FLOAT DEFAULT 0"), ("descripcion", "NVARCHAR(MAX) DEFAULT ''"),
            ("obs_decision", "NVARCHAR(MAX) DEFAULT ''"),
            ("devuelto_a", "NVARCHAR(50) DEFAULT ''"),
            ("parent_expediente_id", "INT DEFAULT NULL"),
            ("status_riesgo_obs", "NVARCHAR(MAX) DEFAULT ''"),
            ("estado_workflow", "NVARCHAR(100) DEFAULT 'EN EVALUACIÓN - CUMPLIMIENTO'"),
            ("eliminado", "BIT NOT NULL DEFAULT 0")
        ]
        for col, dtype in columns_wf:
            if not column_exists('expedientes_wf', col):
                conn.execute(text(f"ALTER TABLE expedientes_wf ADD {col} {dtype}"))

        # ── Expedientes Automotrices ──────────────────────────────
        if not table_exists('expedientes_auto'):
            conn.execute(text('''CREATE TABLE expedientes_auto (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fecha NVARCHAR(50), cliente NVARCHAR(255), cedula NVARCHAR(50),
                telefono NVARCHAR(50) DEFAULT '',
                marca NVARCHAR(100) DEFAULT '', modelo NVARCHAR(100) DEFAULT '',
                anio INT DEFAULT 0, vin NVARCHAR(100) DEFAULT '',
                precio_vehiculo FLOAT DEFAULT 0,
                tipo_vehiculo NVARCHAR(50) DEFAULT 'Nuevo',
                monto FLOAT DEFAULT 0, plazo_meses INT DEFAULT 48,
                cuota_est FLOAT DEFAULT 0, enganche FLOAT DEFAULT 0,
                moneda NVARCHAR(10) DEFAULT 'USD',
                status_comp INT DEFAULT 0,
                riesgo_aml NVARCHAR(50) DEFAULT 'Bajo',
                origen_fondos NVARCHAR(MAX) DEFAULT '',
                check_pep INT DEFAULT 0, check_sanciones INT DEFAULT 0,
                obs_comp NVARCHAR(MAX) DEFAULT '',
                status_leg INT DEFAULT 0,
                seguro_vehiculo INT DEFAULT 0,
                registro_lien INT DEFAULT 0,
                ltv_ratio FLOAT DEFAULT 0,
                fecha_vencimiento_seguro NVARCHAR(50) DEFAULT '',
                obs_leg NVARCHAR(MAX) DEFAULT '',
                status_riesgo INT DEFAULT 0,
                ingreso_mensual FLOAT DEFAULT 0,
                gastos_mensuales FLOAT DEFAULT 0,
                dti_ratio FLOAT DEFAULT 0,
                estabilidad_laboral FLOAT DEFAULT 5.0,
                estres_aplicado INT DEFAULT 0,
                score_f FLOAT DEFAULT 0, rm_score FLOAT DEFAULT 0,
                tasa_sugerida FLOAT DEFAULT 0,
                obs_riesgo NVARCHAR(MAX) DEFAULT '', covenants NVARCHAR(MAX) DEFAULT '',
                dictamen NVARCHAR(50) DEFAULT 'PENDIENTE',
                tasa_aprobada FLOAT DEFAULT 0,
                aprobado_por NVARCHAR(255) DEFAULT '',
                fecha_decision NVARCHAR(50) DEFAULT '',
                eliminado BIT NOT NULL DEFAULT 0)'''))

        # Columnas incrementales expedientes_auto
        columns_auto = [
            ("cliente_id", "INT DEFAULT NULL"), ("plan_generado", "INT DEFAULT 0"),
            ("estado_cobranza", "NVARCHAR(50) DEFAULT 'Al día'"), ("tipo_producto", "NVARCHAR(50) DEFAULT 'Corporativo'"),
            ("vehiculo_placa", "NVARCHAR(20) DEFAULT ''"), ("seguro_empresa", "NVARCHAR(100) DEFAULT ''"),
            ("seguro_poliza", "NVARCHAR(100) DEFAULT ''"), ("seguro_vigencia", "NVARCHAR(50) DEFAULT ''"),
            ("descripcion", "NVARCHAR(MAX) DEFAULT ''"),
            ("obs_decision", "NVARCHAR(MAX) DEFAULT ''"),
            ("devuelto_a", "NVARCHAR(50) DEFAULT ''"),
            ("parent_expediente_id", "INT DEFAULT NULL"),
            ("status_riesgo_obs", "NVARCHAR(MAX) DEFAULT ''"),
            ("ocupacion", "NVARCHAR(100) DEFAULT ''"),
            ("empleador", "NVARCHAR(100) DEFAULT ''"),
            ("estado_workflow", "NVARCHAR(100) DEFAULT 'EN EVALUACIÓN - CUMPLIMIENTO'"),
            ("eliminado", "BIT NOT NULL DEFAULT 0")
        ]
        for col, dtype in columns_auto:
            if not column_exists('expedientes_auto', col):
                conn.execute(text(f"ALTER TABLE expedientes_auto ADD {col} {dtype}"))

        for _t in ('expedientes_wf', 'expedientes_auto'):
            conn.execute(text(f"UPDATE {_t} SET eliminado = 0 WHERE eliminado IS NULL"))
            conn.execute(text(f"UPDATE {_t} SET estado_workflow = 'EN EVALUACIÓN - CUMPLIMIENTO' WHERE estado_workflow IS NULL OR estado_workflow = ''"))
            conn.execute(text(f"UPDATE {_t} SET estado_workflow = 'APROBADO' WHERE dictamen = 'APROBADO' AND estado_workflow = 'EN EVALUACIÓN - CUMPLIMIENTO'"))
            conn.execute(text(f"UPDATE {_t} SET estado_workflow = 'CERRADO - RECHAZADO CUMPLIMIENTO' WHERE dictamen IN ('RECHAZADO', 'DENEGADO') AND status_comp = 0 AND estado_workflow = 'EN EVALUACIÓN - CUMPLIMIENTO'"))
            conn.execute(text(f"UPDATE {_t} SET estado_workflow = 'CERRADO - RECHAZADO' WHERE dictamen IN ('RECHAZADO', 'DENEGADO') AND status_comp = 1 AND estado_workflow = 'EN EVALUACIÓN - CUMPLIMIENTO'"))
            conn.execute(text(f"UPDATE {_t} SET estado_workflow = 'SUBSANACIÓN COMERCIAL' WHERE dictamen LIKE 'REVISI%' AND estado_workflow = 'EN EVALUACIÓN - CUMPLIMIENTO'"))
            conn.execute(text(f"UPDATE {_t} SET estado_workflow = 'EN EVALUACIÓN - CRÉDITO Y LEGAL' WHERE dictamen = 'PENDIENTE' AND status_comp = 1 AND estado_workflow = 'EN EVALUACIÓN - CUMPLIMIENTO'"))

        # ── Clientes ──────────────────────────────────────────────
        if not table_exists('clientes'):
            conn.execute(text('''CREATE TABLE clientes (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fecha_registro NVARCHAR(50),
                tipo NVARCHAR(20) DEFAULT 'Natural',
                nombre NVARCHAR(255), cedula_rif NVARCHAR(50),
                fecha_nacimiento NVARCHAR(50) DEFAULT '',
                nacionalidad NVARCHAR(100) DEFAULT 'Venezolana',
                telefono NVARCHAR(50) DEFAULT '', email NVARCHAR(255) DEFAULT '',
                direccion NVARCHAR(MAX) DEFAULT '',
                actividad_economica NVARCHAR(MAX) DEFAULT '',
                nombre_rep NVARCHAR(255) DEFAULT '',
                cedula_rep NVARCHAR(50) DEFAULT '',
                cargo_rep NVARCHAR(100) DEFAULT '',
                docs_json NVARCHAR(MAX) DEFAULT '{}',
                kyc_status NVARCHAR(50) DEFAULT 'Prospecto',
                obs_kyc NVARCHAR(MAX) DEFAULT '',
                kyc_aprobado_por NVARCHAR(255) DEFAULT '',
                kyc_fecha NVARCHAR(50) DEFAULT '')'''))

        # ── Documentos Cliente (KYC) ──────────────────────────────
        if not table_exists('documentos_cliente'):
            conn.execute(text('''CREATE TABLE documentos_cliente (
                id INT IDENTITY(1,1) PRIMARY KEY,
                cliente_id INT NOT NULL,
                doc_name NVARCHAR(255) NOT NULL DEFAULT '',
                file_name NVARCHAR(255) NOT NULL,
                carpeta NVARCHAR(500) NOT NULL DEFAULT '',
                fecha_carga NVARCHAR(50) NOT NULL DEFAULT '',
                fecha_sync NVARCHAR(50) NOT NULL DEFAULT '',
                sp_sync_status NVARCHAR(50) NOT NULL DEFAULT 'No Sincronizado')'''))

        # ── Documentos Expediente (Operación) ─────────────────────
        if not table_exists('documentos_expediente'):
            conn.execute(text('''CREATE TABLE documentos_expediente (
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
                eliminado BIT NOT NULL DEFAULT 0)'''))

        # ── Tareas Workflow ───────────────────────────────────────
        if not table_exists('tareas_workflow'):
            conn.execute(text('''CREATE TABLE tareas_workflow (
                id INT IDENTITY(1,1) PRIMARY KEY,
                expediente_id INT NOT NULL,
                tipo_expediente NVARCHAR(50) NOT NULL,
                etapa NVARCHAR(100) NOT NULL,
                estado NVARCHAR(50) NOT NULL DEFAULT 'PENDIENTE',
                origen NVARCHAR(100) DEFAULT '',
                observaciones NVARCHAR(MAX) DEFAULT '',
                creado_por NVARCHAR(255) DEFAULT '',
                fecha_creacion NVARCHAR(50) DEFAULT '',
                fecha_cierre NVARCHAR(50) DEFAULT '')'''))

        # ── Evaluaciones Riesgo (Hojas de trabajo) ────────────────
        if not table_exists('evaluaciones_riesgo_corp'):
            conn.execute(text('''CREATE TABLE evaluaciones_riesgo_corp (
                expediente_id INT PRIMARY KEY,
                activos_corrientes FLOAT DEFAULT 0, pasivos_corrientes FLOAT DEFAULT 0,
                pasivos_totales FLOAT DEFAULT 0, patrimonio FLOAT DEFAULT 0,
                activos_totales FLOAT DEFAULT 0, caja_equivalentes FLOAT DEFAULT 0,
                cuentas_por_cobrar FLOAT DEFAULT 0, cuentas_por_pagar FLOAT DEFAULT 0,
                inventarios FLOAT DEFAULT 0, deuda_financiera_total FLOAT DEFAULT 0,
                utilidades_retenidas FLOAT DEFAULT 0, valor_patrimonio_mercado FLOAT DEFAULT 0,
                ebitda FLOAT DEFAULT 0, gastos_financieros FLOAT DEFAULT 0,
                depreciacion_amortizacion FLOAT DEFAULT 0, costo_ventas FLOAT DEFAULT 0,
                impuestos_estimados FLOAT DEFAULT 0, utilidad_neta FLOAT DEFAULT 0,
                ingresos_mensuales FLOAT DEFAULT 0, cuota_mensual FLOAT DEFAULT 0,
                aplicar_estres BIT DEFAULT 0, kc_score FLOAT DEFAULT 0,
                monto_credito FLOAT DEFAULT 0, tasa_interes_anual FLOAT DEFAULT 0,
                plazo_meses INT DEFAULT 0, meses_gracia INT DEFAULT 0,
                moneda NVARCHAR(10) DEFAULT 'USD', covenants NVARCHAR(MAX) DEFAULT '',
                obs_riesgo NVARCHAR(MAX) DEFAULT '', entradas_ihp_json NVARCHAR(MAX) DEFAULT '{}',
                actualizado_por NVARCHAR(255) DEFAULT '', fecha_actualizacion NVARCHAR(50) DEFAULT '')'''))

        if not table_exists('evaluaciones_riesgo_auto'):
            conn.execute(text('''CREATE TABLE evaluaciones_riesgo_auto (
                expediente_id INT PRIMARY KEY,
                ingreso_mensual FLOAT DEFAULT 0, gastos_fijos FLOAT DEFAULT 0,
                cuota_mensual FLOAT DEFAULT 0, ltv_ratio FLOAT DEFAULT 0,
                estabilidad_laboral FLOAT DEFAULT 0, aplicar_estres BIT DEFAULT 0,
                kc_score FLOAT DEFAULT 0, moneda NVARCHAR(10) DEFAULT 'USD',
                covenants NVARCHAR(MAX) DEFAULT '', obs_riesgo NVARCHAR(MAX) DEFAULT '',
                actualizado_por NVARCHAR(255) DEFAULT '', fecha_actualizacion NVARCHAR(50) DEFAULT '')'''))

        # ── Plan de Pagos ─────────────────────────────────────────
        if not table_exists('plan_pagos'):
            conn.execute(text('''CREATE TABLE plan_pagos (
                id INT IDENTITY(1,1) PRIMARY KEY,
                expediente_id INT NOT NULL,
                tipo_expediente NVARCHAR(50) NOT NULL,
                periodo INT,
                fecha_pago NVARCHAR(50),
                cuota FLOAT DEFAULT 0,
                capital FLOAT DEFAULT 0,
                interes FLOAT DEFAULT 0,
                saldo FLOAT DEFAULT 0,
                estado NVARCHAR(50) DEFAULT 'PENDIENTE')'''))

        # ── Gestiones de Cobranza ─────────────────────────────────
        if not table_exists('gestiones_cobranza'):
            conn.execute(text('''CREATE TABLE gestiones_cobranza (
                id INT IDENTITY(1,1) PRIMARY KEY,
                expediente_id INT NOT NULL,
                tipo_expediente NVARCHAR(50) NOT NULL,
                fecha NVARCHAR(50),
                tipo_gestion NVARCHAR(50) DEFAULT 'Llamada',
                responsable NVARCHAR(255) DEFAULT '',
                resultado NVARCHAR(MAX) DEFAULT '',
                proxima_accion NVARCHAR(MAX) DEFAULT '',
                fecha_proxima NVARCHAR(50) DEFAULT '',
                obs NVARCHAR(MAX) DEFAULT '')'''))

        # ── Pagos Recibidos ───────────────────────────────────────
        if not table_exists('pagos_recibidos'):
            conn.execute(text('''CREATE TABLE pagos_recibidos (
                id INT IDENTITY(1,1) PRIMARY KEY,
                expediente_id INT NOT NULL,
                tipo_expediente NVARCHAR(50) NOT NULL,
                fecha_pago NVARCHAR(50),
                monto FLOAT DEFAULT 0,
                referencia NVARCHAR(255) DEFAULT '',
                creado_en DATETIME DEFAULT GETDATE())'''))

        # Columnas incrementales para pagos_recibidos (Caja Mixta)
        columns_pagos = [
            ("moneda", "NVARCHAR(10) DEFAULT 'USD'"),
            ("tasa_cambio", "FLOAT DEFAULT 1.0"),
            ("monto_ves", "FLOAT DEFAULT 0"),
            ("metodos_json", "NVARCHAR(MAX) DEFAULT ''"),
            ("cascada_json", "NVARCHAR(MAX) DEFAULT ''"),
            ("cajero", "NVARCHAR(255) DEFAULT ''"),
            ("comprobante_url", "NVARCHAR(500) DEFAULT ''"),
            ("saldo_anterior", "FLOAT DEFAULT 0"),
            ("nuevo_saldo", "FLOAT DEFAULT 0"),
            ("abono_destino", "NVARCHAR(50) DEFAULT 'reducir_cuota'"),
            ("notas", "NVARCHAR(MAX) DEFAULT ''"),
            ("creado_en", "DATETIME DEFAULT GETDATE()"),
        ]
        for col, dtype in columns_pagos:
            if not column_exists('pagos_recibidos', col):
                conn.execute(text(f"ALTER TABLE pagos_recibidos ADD {col} {dtype}"))

        conn.execute(text("UPDATE pagos_recibidos SET creado_en = GETDATE() WHERE creado_en IS NULL"))

        # ── Arqueos de Caja ───────────────────────────────────────
        if not table_exists('arqueos_caja'):
            conn.execute(text('''CREATE TABLE arqueos_caja (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fecha NVARCHAR(50) NOT NULL,
                cajero NVARCHAR(255) NOT NULL,
                total_sistema_usd FLOAT DEFAULT 0,
                total_sistema_ves FLOAT DEFAULT 0,
                efectivo_declarado_usd FLOAT DEFAULT 0,
                efectivo_declarado_ves FLOAT DEFAULT 0,
                pos_declarado_ves FLOAT DEFAULT 0,
                transferencias_declarado_ves FLOAT DEFAULT 0,
                diferencia_usd FLOAT DEFAULT 0,
                diferencia_ves FLOAT DEFAULT 0,
                estado NVARCHAR(50) DEFAULT 'CERRADO',
                observaciones NVARCHAR(MAX) DEFAULT '',
                fecha_cierre NVARCHAR(50) DEFAULT '')'''))

        # ── Usuarios ──────────────────────────────────────────────
        if not table_exists('usuarios'):
            conn.execute(text('''CREATE TABLE usuarios (
                [user] NVARCHAR(255) PRIMARY KEY, 
                [password] NVARCHAR(255), 
                [role] NVARCHAR(50))'''))

        # Admin por defecto
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@kfg.com")
        admin_pwd = os.getenv("DEFAULT_ADMIN_PASSWORD", "kfg2026")
        hashed_admin_pwd = SecurityService.hash_password(admin_pwd)

        res = conn.execute(text("SELECT 1 FROM usuarios WHERE [user] = :u"), {"u": admin_email}).fetchone()
        if not res:
            conn.execute(text("INSERT INTO usuarios ([user], [password], [role]) VALUES (:u, :p, 'Superadmin')"),
                         {"u": admin_email, "p": hashed_admin_pwd})

        # ── Parámetros de scoring ─────────────────────────────────
        if not table_exists('config_parametros'):
            conn.execute(text('''CREATE TABLE config_parametros (clave NVARCHAR(100) PRIMARY KEY, valor FLOAT)'''))

        params = [
            ('w_liq', 1.0), ('w_sol', 1.0), ('w_cob', 1.0), ('kc_boost_max', 20.0), ('tasa_base', 12.0),
            ('factor_riesgo', 2.0), ('w_cap', 1.0), ('w_ltv_auto', 1.0), ('w_est', 1.0),
            ('kc_boost_max_auto', 20.0), ('tasa_base_auto', 10.0), ('factor_riesgo_auto', 1.5)
        ]
        for k, v in params:
            res = conn.execute(text("SELECT 1 FROM config_parametros WHERE clave = :k"), {"k": k}).fetchone()
            if not res:
                conn.execute(text("INSERT INTO config_parametros (clave, valor) VALUES (:k, :v)"), {"k": k, "v": v})
