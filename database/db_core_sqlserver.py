import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from services.security_service import SecurityService

load_dotenv()

# ── Configuración de SQL Server ──────────────────────────────────────────────
RAW_DB_URL = os.getenv("DATABASE_URL", "")

def get_sqlalchemy_url(url):
    """Convierte la URL de configuración a un formato aceptado por SQLAlchemy."""
    if not url.startswith("sqlserver://"):
        # Si ya es una cadena ODBC o algo distinto, intentamos tratarla como tal
        return url
        
    try:
        # Ejemplo: sqlserver://127.0.0.1:1433;database=...;user=...;password=...;
        clean_url = url.replace("sqlserver://", "")
        parts = clean_url.split(";")
        server_port = parts[0]
        params = {p.split("=")[0].lower(): p.split("=")[1] for p in parts[1:] if "=" in p}
        
        server = server_port.split(":")[0]
        port = server_port.split(":")[1] if ":" in server_port else "1433"
        
        driver = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")
        db = params.get("database", "kfg_ecosystem")
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

# Inicialización del Engine global
DATABASE_URI = get_sqlalchemy_url(RAW_DB_URL)
engine = create_engine(DATABASE_URI, pool_pre_ping=True)

def get_connection():
    """Retorna una conexión compatible con Pandas (Engine o Connection)."""
    # Para Pandas >= 2.0, se recomienda pasar el engine directamente
    return engine

def db_action(query, params=()):
    """Ejecuta una consulta SQL genérica que requiere commit usando SQLAlchemy."""
    # En SQLAlchemy, los parámetros se pasan como un diccionario o kwargs
    # Pero para mantener compatibilidad con el estilo SQLite (?), usamos text() 
    # y mapeo si fuera necesario. Sin embargo, pyodbc soporta '?' vía SQLAlchemy.
    with engine.begin() as conn:
        try:
            # SQLAlchemy text() maneja la ejecución. Los parámetros se pasan al execute.
            conn.execute(text(query), params)
        except Exception as e:
            print(f"Error en db_action: {e}")
            raise e

def init_db():
    """Inicializa la base de datos en SQL Server usando SQLAlchemy."""
    with engine.begin() as conn:
        # Helper para verificar existencia de tabla
        def table_exists(name):
            q = text("SELECT 1 FROM sys.tables WHERE name = :name")
            return conn.execute(q, {"name": name}).fetchone() is not None

        # Helper para verificar existencia de columna
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
                fecha_vencimiento_garantia NVARCHAR(50), ltv_ratio FLOAT DEFAULT 0)'''))

        # Columnas incrementales
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
            ("ingresos_mensuales", "FLOAT DEFAULT 0"), ("descripcion", "NVARCHAR(MAX) DEFAULT ''")
        ]
        for col, dtype in columns_wf:
            if not column_exists('expedientes_wf', col):
                conn.execute(text(f"ALTER TABLE expedientes_wf ADD {col} {dtype}"))

        # ── Expedientes Automotrices ──────────────────────────────
        if not table_exists('expedientes_auto'):
            conn.execute(text('''CREATE TABLE expedientes_auto (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fecha NVARCHAR(50), cliente NVARCHAR(255), cedula NVARCHAR(50),
                ocupacion NVARCHAR(255) DEFAULT '', empleador NVARCHAR(255) DEFAULT '',
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
                fecha_decision NVARCHAR(50) DEFAULT '')'''))

        # Columnas incrementales
        columns_auto = [
            ("cliente_id", "INT DEFAULT NULL"), ("plan_generado", "INT DEFAULT 0"),
            ("estado_cobranza", "NVARCHAR(50) DEFAULT 'Al día'"), ("tipo_producto", "NVARCHAR(50) DEFAULT 'Corporativo'"),
            ("vehiculo_placa", "NVARCHAR(20) DEFAULT ''"), ("seguro_empresa", "NVARCHAR(100) DEFAULT ''"),
            ("seguro_poliza", "NVARCHAR(100) DEFAULT ''"), ("seguro_vigencia", "NVARCHAR(50) DEFAULT ''"),
            ("descripcion", "NVARCHAR(MAX) DEFAULT ''")
        ]
        for col, dtype in columns_auto:
            if not column_exists('expedientes_auto', col):
                conn.execute(text(f"ALTER TABLE expedientes_auto ADD {col} {dtype}"))

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

        # ── Usuarios ──────────────────────────────────────────────
        if not table_exists('usuarios'):
            conn.execute(text('''CREATE TABLE usuarios (
                [user] NVARCHAR(255) PRIMARY KEY, 
                [password] NVARCHAR(255), 
                [role] NVARCHAR(50))'''))
        
        # Admin por defecto
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "jgeorges@kz.finance")
        admin_pwd = os.getenv("DEFAULT_ADMIN_PASSWORD", "kfg2026")
        hashed_admin_pwd = SecurityService.hash_password(admin_pwd)
        
        res = conn.execute(text("SELECT 1 FROM usuarios WHERE [user] = :u"), {"u": admin_email}).fetchone()
        if not res:
            conn.execute(text("INSERT INTO usuarios ([user], [password], [role]) VALUES (:u, :p, 'Superadmin')"),
                         {"u": admin_email, "p": hashed_admin_pwd})

        # ── Parámetros ────────────────────────────────────────────
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
