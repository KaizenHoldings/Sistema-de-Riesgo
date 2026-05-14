import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# Obtiene la ruta absoluta de la base de datos original en el nivel superior (KFG_Tools/kfg_ecosystem.db)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../kfg_ecosystem.db'))

def get_connection():
    """Retorna una conexión a la base de datos con un timeout configurado."""
    return sqlite3.connect(DB_PATH, timeout=10)

def db_action(query, params=()):
    """Ejecuta una consulta SQL genérica que requiere commit (INSERT, UPDATE, DELETE)."""
    conn = get_connection()
    curr = conn.cursor()
    curr.execute(query, params)
    conn.commit()
    conn.close()

def init_db():
    """Inicializa la base de datos y crea/actualiza el esquema si es necesario."""
    conn = get_connection()
    c = conn.cursor()

    # ── Expedientes Corporativos ──────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS expedientes_wf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT, cliente TEXT, rif TEXT, monto REAL,
        status_comp INT DEFAULT 0, riesgo_aml TEXT DEFAULT 'Bajo',
        origen_fondos TEXT DEFAULT '', obs_comp TEXT DEFAULT '',
        status_leg INT DEFAULT 0, v_garantia REAL DEFAULT 0, obs_leg TEXT DEFAULT '',
        status_riesgo INT DEFAULT 0, score_f REAL DEFAULT 0,
        rm_score REAL DEFAULT 0, obs_riesgo TEXT DEFAULT '',
        ac REAL DEFAULT 0, pc REAL DEFAULT 1, eb REAL DEFAULT 0, gf REAL DEFAULT 1,
        pt REAL DEFAULT 0, pa REAL DEFAULT 1,
        dictamen TEXT DEFAULT 'PENDIENTE',
        garantias_json TEXT DEFAULT '[]', custodia_fisica INT DEFAULT 0,
        fecha_vencimiento_garantia TEXT, ltv_ratio REAL DEFAULT 0)''')

    for col, dtype in [
        ("cuota_est", "REAL DEFAULT 0"), ("ing_mensuales", "REAL DEFAULT 0"),
        ("moneda", "TEXT DEFAULT 'USD'"), ("estres_aplicado", "INT DEFAULT 0"),
        ("dscr", "REAL DEFAULT 0"), ("margen_ebitda", "REAL DEFAULT 0"),
        ("check_pep", "INT DEFAULT 0"), ("check_sanciones", "INT DEFAULT 0"),
        ("tasa_sugerida", "REAL DEFAULT 0"), ("tasa_aprobada", "REAL DEFAULT 0"),
        ("aprobado_por", "TEXT DEFAULT ''"), ("fecha_decision", "TEXT DEFAULT ''"),
        ("covenants", "TEXT DEFAULT ''"), ("plazo_meses", "INT DEFAULT 36")
    ]:
        try: c.execute(f"ALTER TABLE expedientes_wf ADD COLUMN {col} {dtype}")
        except Exception: pass

    # ── Expedientes Automotrices ──────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS expedientes_auto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT, cliente TEXT, cedula TEXT,
        ocupacion TEXT DEFAULT '', empleador TEXT DEFAULT '',
        telefono TEXT DEFAULT '',
        marca TEXT DEFAULT '', modelo TEXT DEFAULT '',
        anio INT DEFAULT 0, vin TEXT DEFAULT '',
        precio_vehiculo REAL DEFAULT 0,
        tipo_vehiculo TEXT DEFAULT 'Nuevo',
        monto REAL DEFAULT 0, plazo_meses INT DEFAULT 48,
        cuota_est REAL DEFAULT 0, enganche REAL DEFAULT 0,
        moneda TEXT DEFAULT 'USD',
        status_comp INT DEFAULT 0,
        riesgo_aml TEXT DEFAULT 'Bajo',
        origen_fondos TEXT DEFAULT '',
        check_pep INT DEFAULT 0, check_sanciones INT DEFAULT 0,
        obs_comp TEXT DEFAULT '',
        status_leg INT DEFAULT 0,
        seguro_vehiculo INT DEFAULT 0,
        registro_lien INT DEFAULT 0,
        ltv_ratio REAL DEFAULT 0,
        fecha_vencimiento_seguro TEXT DEFAULT '',
        obs_leg TEXT DEFAULT '',
        status_riesgo INT DEFAULT 0,
        ingreso_mensual REAL DEFAULT 0,
        gastos_mensuales REAL DEFAULT 0,
        dti_ratio REAL DEFAULT 0,
        estabilidad_laboral REAL DEFAULT 5.0,
        estres_aplicado INT DEFAULT 0,
        score_f REAL DEFAULT 0, rm_score REAL DEFAULT 0,
        tasa_sugerida REAL DEFAULT 0,
        obs_riesgo TEXT DEFAULT '', covenants TEXT DEFAULT '',
        dictamen TEXT DEFAULT 'PENDIENTE',
        tasa_aprobada REAL DEFAULT 0,
        aprobado_por TEXT DEFAULT '',
        fecha_decision TEXT DEFAULT '')''')

    # ── Clientes (Onboarding / KYC) ───────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_registro TEXT,
        tipo TEXT DEFAULT 'Natural',
        nombre TEXT, cedula_rif TEXT,
        fecha_nacimiento TEXT DEFAULT '',
        nacionalidad TEXT DEFAULT 'Venezolana',
        telefono TEXT DEFAULT '', email TEXT DEFAULT '',
        direccion TEXT DEFAULT '',
        actividad_economica TEXT DEFAULT '',
        nombre_rep TEXT DEFAULT '',
        cedula_rep TEXT DEFAULT '',
        cargo_rep TEXT DEFAULT '',
        docs_json TEXT DEFAULT '{}',
        kyc_status TEXT DEFAULT 'Prospecto',
        obs_kyc TEXT DEFAULT '',
        kyc_aprobado_por TEXT DEFAULT '',
        kyc_fecha TEXT DEFAULT '')''')

    # ── Plan de Pagos / Amortización ──────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS plan_pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expediente_id INTEGER NOT NULL,
        tipo_expediente TEXT NOT NULL,
        periodo INTEGER,
        fecha_pago TEXT,
        cuota REAL DEFAULT 0,
        capital REAL DEFAULT 0,
        interes REAL DEFAULT 0,
        saldo REAL DEFAULT 0,
        estado TEXT DEFAULT 'PENDIENTE')''')

    # Migración: vincular expedientes a cliente registrado
    for tbl in ('expedientes_wf', 'expedientes_auto'):
        try: c.execute(f"ALTER TABLE {tbl} ADD COLUMN cliente_id INTEGER DEFAULT NULL")
        except Exception: pass
    for tbl in ('expedientes_wf', 'expedientes_auto'):
        try: c.execute(f"ALTER TABLE {tbl} ADD COLUMN plan_generado INTEGER DEFAULT 0")
        except Exception: pass

    # ── Gestiones de Cobranza ─────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS gestiones_cobranza (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expediente_id INTEGER NOT NULL,
        tipo_expediente TEXT NOT NULL,
        fecha TEXT,
        tipo_gestion TEXT DEFAULT 'Llamada',
        responsable TEXT DEFAULT '',
        resultado TEXT DEFAULT '',
        proxima_accion TEXT DEFAULT '',
        fecha_proxima TEXT DEFAULT '',
        obs TEXT DEFAULT '')''')

    # Migración: estado de cobranza en expedientes aprobados
    for tbl in ('expedientes_wf', 'expedientes_auto'):
        try: c.execute(f"ALTER TABLE {tbl} ADD COLUMN estado_cobranza TEXT DEFAULT 'Al día'")
        except Exception: pass

    # Migración: tipo_producto e info adicional de vehículo/póliza
    for tbl in ('expedientes_wf', 'expedientes_auto'):
        try: c.execute(f"ALTER TABLE {tbl} ADD COLUMN tipo_producto TEXT DEFAULT 'Corporativo'")
        except Exception: pass
    auto_extra = [
        ("vehiculo_placa",  "TEXT DEFAULT ''"),
        ("seguro_empresa",  "TEXT DEFAULT ''"),
        ("seguro_poliza",   "TEXT DEFAULT ''"),
        ("seguro_vigencia", "TEXT DEFAULT ''"),
    ]
    for col, dtype in auto_extra:
        try: c.execute(f"ALTER TABLE expedientes_auto ADD COLUMN {col} {dtype}")
        except Exception: pass
    # ingresos_mensuales en expedientes_wf (alias de ing_mensuales ya existente)
    try: c.execute("ALTER TABLE expedientes_wf ADD COLUMN ingresos_mensuales REAL DEFAULT 0")
    except Exception: pass

    # ── Pagos Recibidos (amortizaciones confirmadas) ──────────
    c.execute('''CREATE TABLE IF NOT EXISTS pagos_recibidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expediente_id INTEGER NOT NULL,
        tipo_expediente TEXT NOT NULL,
        fecha_pago TEXT,
        monto REAL DEFAULT 0,
        referencia TEXT DEFAULT '')''')

    # ── Usuarios ──────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (user TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "jgeorges@kz.finance")
    admin_pwd = os.getenv("DEFAULT_ADMIN_PASSWORD", "kfg2026")
    c.execute("INSERT OR IGNORE INTO usuarios VALUES (?, ?, 'Superadmin')", (admin_email, admin_pwd))

    # ── Parámetros de Configuración ───────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS config_parametros
                 (clave TEXT PRIMARY KEY, valor REAL)''')
    for k, v in [
        ('w_liq', 1.0), ('w_sol', 1.0), ('w_cob', 1.0),
        ('kc_boost_max', 20.0), ('tasa_base', 12.0), ('factor_riesgo', 2.0),
        ('w_cap', 1.0), ('w_ltv_auto', 1.0), ('w_est', 1.0),
        ('kc_boost_max_auto', 20.0), ('tasa_base_auto', 10.0), ('factor_riesgo_auto', 1.5)
    ]:
        c.execute("INSERT OR IGNORE INTO config_parametros VALUES (?,?)", (k, v))

    c.execute("UPDATE expedientes_wf SET dictamen='PENDIENTE' WHERE dictamen IS NULL")
    c.execute("UPDATE expedientes_auto SET dictamen='PENDIENTE' WHERE dictamen IS NULL")
    conn.commit()
    conn.close()
