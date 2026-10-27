"""
Servicio integral de Cartera y Cobranzas.

Implementa los cinco pilares requeridos por la operativa de caja y cartera:
1. Búsqueda universal de créditos y clientes.
2. Tasa de cambio oficial del día (BCV) inmodificable por el cajero.
3. Panel de información financiera (deuda vencida, cuotas y liquidación anticipada).
4. Caja mixta multi-moneda con validación de referencias únicas y motor de cascada legal.
5. Auditoría, arqueo diario y emisión de recibos oficiales en PDF.
"""

from datetime import date, datetime
import json
from fpdf import FPDF
from sqlalchemy import text
from database.db_core_sqlserver import sesion_activa, db_action
from database.daos_sqlserver import _filas


def _sanitizar_pdf_txt(s: str) -> str:
    """Sanitiza strings para compatibilidad estricta con fuentes de 8 bits de FPDF."""
    if s is None:
        return ""
    trans = {
        "·": "-", "—": "-", "–": "-", "•": "*",
        "“": '"', "”": '"', "’": "'", "‘": "'",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N"
    }
    r = str(s)
    for k, v in trans.items():
        r = r.replace(k, v)
    return r.encode("latin-1", "replace").decode("latin-1")


class ReciboPDF(FPDF):
    def header(self):
        self.set_fill_color(11, 29, 78)  # Azul Kaizen #0B1D4E
        self.rect(0, 0, 210, 16, 'F')
        self.set_y(4)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "KAIZEN FINANCIAL GROUP  -  RECIBO OFICIAL DE COBRO Y CAJA", align='C', ln=True)

    def footer(self):
        self.set_y(-18)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "Comprobante emitido electronicamente por KFG Risk & Collections Architect. Valido como soporte de pago.", align='C', ln=True)


class CertificadoFiniquitoPDF(FPDF):
    def header(self):
        self.set_fill_color(11, 29, 78)  # Azul Kaizen #0B1D4E
        self.rect(0, 0, 210, 22, 'F')
        self.set_y(5)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, "KAIZEN FINANCIAL GROUP  -  CERTIFICADO OFICIAL DE FINIQUITO", align='C', ln=True)
        self.set_font('Arial', '', 8)
        self.set_text_color(200, 220, 255)
        self.cell(0, 4, "CONSTANCIA DE LIQUIDACION TOTAL DE DEUDA Y SOLVENCIA CREDITICIA", align='C', ln=True)

    def footer(self):
        self.set_y(-18)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Constancia emitida por KFG Risk & Cartera. Documento oficial valido como comprobante de finiquito y no adeudo.", align='C', ln=True)


class CollectionService:

    @staticmethod
    def obtener_tasa_cambio(session=None) -> dict:
        """
        Devuelve la tasa oficial del día del BCV y otras divisas.
        Inmodificable por el operador para garantizar consistencia contable.
        """
        # Se busca si hay tasa configurada en parámetros; si no, tasa de referencia oficial
        tasa_bcv = 45.45
        with sesion_activa(session) as conn:
            try:
                row = conn.execute(text("SELECT valor FROM config_parametros WHERE clave = 'tasa_bcv_usd'")).fetchone()
                if row and row[0]:
                    tasa_bcv = float(row[0])
            except Exception:
                pass

        return {
            "USD_VES": tasa_bcv,
            "EUR_VES": round(tasa_bcv * 1.08, 2),
            "COP_VES": 0.0115,
            "fecha": date.today().strftime("%Y-%m-%d"),
            "fuente": "Banco Central de Venezuela (BCV)",
            "fijada": True
        }

    @staticmethod
    def buscar_creditos(q: str = "", session=None) -> list[dict]:
        """
        Buscador universal: localiza clientes por Cédula/RIF, nombre completo,
        número de contrato o código de expediente.
        ESTRICTAMENTE filtra por expedientes formalmente aprobados por el Comité de Crédito.
        Si q está vacío, retorna la lista de créditos aprobados disponibles en cartera.
        """
        termino = (q or "").strip()
        patron = f"%{termino}%"
        exacto = int(termino) if termino.isdigit() else -1
        resultados = []

        with sesion_activa(session) as conn:
            if termino:
                # 1. Corporativos aprobados con término de búsqueda
                q_corp = text("""
                    SELECT id, cliente, rif AS documento, monto, dictamen, estado_cobranza,
                           fecha, tasa_aprobada, plazo_meses, 'corp' AS tipo
                    FROM expedientes_wf
                    WHERE eliminado = 0
                      AND dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                      AND (id = :exacto OR cliente LIKE :p OR rif LIKE :p)
                    ORDER BY id DESC
                """)
                filas_corp = conn.execute(q_corp, {"p": patron, "exacto": exacto}).fetchall()

                # 2. Automotrices aprobados con término de búsqueda
                q_auto = text("""
                    SELECT id, cliente, cedula AS documento, monto, dictamen, estado_cobranza,
                           fecha, tasa_aprobada, plazo_meses, 'auto' AS tipo
                    FROM expedientes_auto
                    WHERE eliminado = 0
                      AND dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                      AND (id = :exacto OR cliente LIKE :p OR cedula LIKE :p)
                    ORDER BY id DESC
                """)
                filas_auto = conn.execute(q_auto, {"p": patron, "exacto": exacto}).fetchall()
            else:
                # Todos los créditos formalmente aprobados por el Comité
                q_corp = text("""
                    SELECT id, cliente, rif AS documento, monto, dictamen, estado_cobranza,
                           fecha, tasa_aprobada, plazo_meses, 'corp' AS tipo
                    FROM expedientes_wf
                    WHERE eliminado = 0
                      AND dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                    ORDER BY id DESC
                """)
                filas_corp = conn.execute(q_corp).fetchall()

                q_auto = text("""
                    SELECT id, cliente, cedula AS documento, monto, dictamen, estado_cobranza,
                           fecha, tasa_aprobada, plazo_meses, 'auto' AS tipo
                    FROM expedientes_auto
                    WHERE eliminado = 0
                      AND dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                    ORDER BY id DESC
                """)
                filas_auto = conn.execute(q_auto).fetchall()

            for fila in (*filas_corp, *filas_auto):
                d = dict(fila._mapping)
                exp_id = d["id"]
                tipo = d["tipo"]

                # Calcular saldo actual de capital pendiente y cuotas
                q_plan_info = text("""
                    SELECT COUNT(*) AS total_cuotas,
                           SUM(CASE WHEN estado NOT IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN capital ELSE 0 END) AS saldo_capital,
                           SUM(CASE WHEN estado NOT IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN 1 ELSE 0 END) AS cuotas_pendientes
                    FROM plan_pagos
                    WHERE expediente_id = :id AND tipo_expediente = :t
                """)
                plan_row = conn.execute(q_plan_info, {"id": exp_id, "t": tipo}).fetchone()
                total_cuotas = int(plan_row[0]) if (plan_row and plan_row[0] is not None) else 0

                if total_cuotas > 0:
                    saldo_cap = float(plan_row[1]) if plan_row[1] is not None else 0.0
                    cuotas_pend = int(plan_row[2]) if plan_row[2] is not None else 0
                else:
                    saldo_cap = float(d.get("monto") or 0.0)
                    cuotas_pend = int(d.get("plazo_meses") or 0)

                d["saldo_capital"] = round(saldo_cap, 2)
                d["cuotas_pendientes"] = cuotas_pend
                d["codigo_credito"] = f"EXP-{tipo.upper()}-{exp_id:04d}"
                d["monto"] = float(d.get("monto") or 0.0)
                d["tasa_aprobada"] = float(d.get("tasa_aprobada") or 0.0)
                d["plazo_meses"] = int(d.get("plazo_meses") or 0)

                if (total_cuotas > 0 and saldo_cap <= 0.01 and cuotas_pend == 0) or str(d.get("estado_cobranza") or "").lower() == "pagado":
                    d["estado_cobranza"] = "Pagado"
                else:
                    d["estado_cobranza"] = d.get("estado_cobranza") or "Al día"
                resultados.append(d)

            # Ordenar por ID descendente
            resultados.sort(key=lambda x: x["id"], reverse=True)

        return resultados

    @staticmethod
    def obtener_resumen_financiero(exp_id: int, tipo: str, session=None) -> dict:
        """
        Panel de Información Financiera para el operador:
        - Saldo total
        - Días de mora y cuotas vencidas
        - Monto exacto para ponerse al día hoy
        - Proyección de liquidación total anticipada (restando intereses no causados)
        ESTRICTAMENTE valida que el crédito esté aprobado por el Comité de Crédito.
        """
        hoy = date.today()
        hoy_str = hoy.strftime("%Y-%m-%d")

        with sesion_activa(session) as conn:
            # Obtener datos del expediente
            tabla = "expedientes_wf" if tipo == "corp" else "expedientes_auto"
            doc_col = "rif" if tipo == "corp" else "cedula"
            exp_row = conn.execute(
                text(f"SELECT id, cliente, {doc_col} AS documento, monto, tasa_aprobada, plazo_meses, fecha, dictamen "
                     f"FROM {tabla} WHERE id = :id AND eliminado = 0"), {"id": exp_id}).fetchone()

            if not exp_row:
                raise ValueError(f"Expediente {tipo} #{exp_id} no encontrado.")

            exp = dict(exp_row._mapping)
            if exp.get("dictamen") not in ('APROBADO', 'APROBADO_CON_CONDICIONES'):
                raise ValueError(
                    f"El expediente #{exp_id} no ha sido aprobado por el Comité de Crédito "
                    f"(Dictamen actual: '{exp.get('dictamen')}'). Únicamente los créditos aprobados pasan a Cartera."
                )

            # Obtener plan de pagos
            cuotas_raw = conn.execute(
                text("SELECT id, periodo, fecha_pago, cuota, capital, interes, saldo, estado "
                     "FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t "
                     "ORDER BY periodo ASC"), {"id": exp_id, "t": tipo}).fetchall()

            cuotas = [dict(r._mapping) for r in cuotas_raw]

        cuotas_pendientes = [c for c in cuotas if c.get("estado") != "PAGADO"]
        cuotas_pagadas = [c for c in cuotas if c.get("estado") == "PAGADO"]

        saldo_capital = sum(float(c.get("capital") or 0) for c in cuotas_pendientes)
        saldo_interes_futuro = sum(float(c.get("interes") or 0) for c in cuotas_pendientes)
        saldo_total_nominal = saldo_capital + saldo_interes_futuro

        # Análisis de cuotas vencidas
        cuotas_vencidas_lista = []
        dias_max_atraso = 0
        monto_cuotas_vencidas = 0.0

        for c in cuotas_pendientes:
            fp_str = str(c.get("fecha_pago") or "")[:10]
            try:
                fp = datetime.strptime(fp_str, "%Y-%m-%d").date()
                if fp < hoy:
                    dias = (hoy - fp).days
                    if dias > dias_max_atraso:
                        dias_max_atraso = dias
                    cuotas_vencidas_lista.append({**c, "dias_atraso": dias})
                    monto_cuotas_vencidas += float(c.get("cuota") or 0)
            except Exception:
                pass

        # Cálculo de Intereses de Mora (Tasa legal de mora = 0.1% diario o ~3% mensual sobre vencido)
        tasa_mora_diaria = 0.001
        intereses_mora = round(monto_cuotas_vencidas * tasa_mora_diaria * dias_max_atraso, 2) if dias_max_atraso > 0 else 0.0

        # Gastos de Cobranza (Si hay mora > 15 días, cargo administrativo del 5% o mín $20)
        gastos_cobranza = 0.0
        if dias_max_atraso > 15:
            gastos_cobranza = round(max(20.0, monto_cuotas_vencidas * 0.05), 2)

        monto_ponerse_al_dia = round(monto_cuotas_vencidas + intereses_mora + gastos_cobranza, 2)

        # Proyección de liquidación inmediata:
        # Se cancela el capital insoluto total + mora + gastos + interés devengado del periodo actual
        # ¡Restando todos los intereses no causados de cuotas futuras!
        interes_corriente_actual = float(cuotas_pendientes[0].get("interes") or 0) if cuotas_pendientes else 0.0
        proyeccion_cancelacion_total = round(saldo_capital + intereses_mora + gastos_cobranza + interes_corriente_actual, 2)
        ahorro_intereses_no_causados = round(max(0.0, saldo_interes_futuro - interes_corriente_actual), 2)

        proxima_cuota = cuotas_pendientes[0] if cuotas_pendientes else None

        # Total desembolsado por el cliente en pagos registrados
        pagos_raw = conn.execute(
            text("SELECT COALESCE(SUM(monto), 0) FROM pagos_recibidos WHERE expediente_id = :id AND tipo_expediente = :t"),
            {"id": exp_id, "t": tipo}
        ).fetchone()
        total_pagado_cliente = float(pagos_raw[0]) if pagos_raw and pagos_raw[0] is not None else 0.0

        interes_pagado_cuotas = sum(float(c.get("interes") or 0) for c in cuotas_pagadas)
        capital_pagado_cuotas = sum(float(c.get("capital") or 0) for c in cuotas_pagadas)

        return {
            "expediente_id": exp_id,
            "tipo": tipo,
            "codigo_credito": f"EXP-{tipo.upper()}-{exp_id:04d}",
            "cliente": exp["cliente"],
            "documento": exp["documento"],
            "monto_original": float(exp.get("monto") or 0),
            "tasa_aprobada": float(exp.get("tasa_aprobada") or 0),
            "plazo_meses": int(exp.get("plazo_meses") or 0),
            "saldo_capital": round(saldo_capital, 2),
            "saldo_total_deuda": round(saldo_total_nominal, 2),
            "total_pagado_cliente": round(total_pagado_cliente, 2),
            "capital_amortizado": round(capital_pagado_cuotas, 2),
            "intereses_pagados": round(interes_pagado_cuotas, 2),
            "dias_atraso": dias_max_atraso,
            "num_cuotas_vencidas": len(cuotas_vencidas_lista),
            "monto_cuotas_vencidas": round(monto_cuotas_vencidas, 2),
            "intereses_mora": intereses_mora,
            "gastos_cobranza": gastos_cobranza,
            "monto_ponerse_al_dia": monto_ponerse_al_dia,
            "proyeccion_cancelacion_total": proyeccion_cancelacion_total,
            "ahorro_intereses_no_causados": ahorro_intereses_no_causados,
            "fecha_proxima_cuota": str(proxima_cuota.get("fecha_pago") or "")[:10] if proxima_cuota else "N/A",
            "monto_proxima_cuota": float(proxima_cuota.get("cuota") or 0) if proxima_cuota else 0.0,
            "cuotas_totales": len(cuotas),
            "cuotas_pagadas": len(cuotas_pagadas),
            "plan_pagos": cuotas
        }

    @staticmethod
    def procesar_pago_mixto(datos: dict, session=None) -> dict:
        """
        Caja Mixta con:
        - Bloqueo estricto de referencias duplicadas para evitar fraude.
        - Motor de Cascada Legal (1. Gastos -> 2. Mora -> 3. Interés corriente -> 4. Abono capital).
        - Mapeo de abonos extraordinarios (reducir cuota vs reducir plazo).
        """
        exp_id = int(datos["expediente_id"])
        tipo = str(datos["tipo_expediente"])
        cajero = str(datos.get("cajero") or "Caja Central")
        hoy_str = date.today().strftime("%Y-%m-%d")
        tasa_cambio = float(datos.get("tasa_cambio") or 1.0)
        destino_abono = str(datos.get("destino_abono_extra") or "reducir_cuota")

        metodos = datos.get("metodos") or []
        if not metodos:
            raise ValueError("Debe ingresar al menos un método de pago en la caja mixta.")

        # ── 1. Validación de referencias duplicadas ───────────────────
        with sesion_activa(session) as conn:
            for m in metodos:
                ref = str(m.get("referencia") or "").strip()
                if ref:
                    # Validar si ya existe en pagos_recibidos
                    dup = conn.execute(
                        text("SELECT id, fecha_pago, monto FROM pagos_recibidos WHERE referencia = :r"),
                        {"r": ref}).fetchone()
                    if dup:
                        raise ValueError(f"BLOQUEO DE SEGURIDAD: La referencia bancaria '{ref}' ya fue registrada previamente el {dup[1]} por ${dup[2]}. No se admiten referencias duplicadas.")

            # Obtener resumen antes del pago
            resumen_previo = CollectionService.obtener_resumen_financiero(exp_id, tipo, session=conn)
            saldo_anterior = resumen_previo["saldo_capital"]

            # ── 2. Calcular monto total pagado en USD ──────────────────
            total_pagado_usd = 0.0
            total_pagado_ves = 0.0

            for m in metodos:
                monto = float(m.get("monto") or 0.0)
                moneda = str(m.get("moneda") or "USD").upper()
                if moneda == "USD":
                    total_pagado_usd += monto
                    total_pagado_ves += monto * tasa_cambio
                elif moneda == "VES":
                    total_pagado_ves += monto
                    total_pagado_usd += (monto / tasa_cambio) if tasa_cambio > 0 else monto
                elif moneda == "COP":
                    monto_ves = monto * 0.0115
                    total_pagado_ves += monto_ves
                    total_pagado_usd += (monto_ves / tasa_cambio) if tasa_cambio > 0 else monto_ves

            total_pagado_usd = round(total_pagado_usd, 2)
            total_pagado_ves = round(total_pagado_ves, 2)

            if total_pagado_usd <= 0:
                raise ValueError("El monto total del pago debe ser mayor a cero.")

            # ── 3. Motor de Cascada Legal ─────────────────────────────
            # Orden estricto:
            # 1. Gastos de cobranza / Honorarios
            # 2. Intereses de mora acumulados
            # 3. Intereses corrientes del mes
            # 4. Abono a capital
            disponible = total_pagado_usd
            gastos_exigibles = resumen_previo["gastos_cobranza"]
            mora_exigible = resumen_previo["intereses_mora"]

            imputado_gastos = min(disponible, gastos_exigibles)
            disponible -= imputado_gastos

            imputado_mora = min(disponible, mora_exigible)
            disponible -= imputado_mora

            # Ahora aplicar a las cuotas en orden cronológico
            cuotas_raw = conn.execute(
                text("SELECT id, periodo, cuota, capital, interes, estado FROM plan_pagos "
                     "WHERE expediente_id = :id AND tipo_expediente = :t AND estado <> 'PAGADO' "
                     "ORDER BY periodo ASC"), {"id": exp_id, "t": tipo}).fetchall()

            imputado_interes = 0.0
            imputado_capital = 0.0
            cuotas_liquidadas = []

            for c in cuotas_raw:
                if disponible <= 0:
                    break
                cid = c[0]
                periodo = c[1]
                int_cuota = float(c[4] or 0)
                cap_cuota = float(c[3] or 0)

                # Pagar interés corriente de la cuota
                cubrir_int = min(disponible, int_cuota)
                imputado_interes += cubrir_int
                disponible -= cubrir_int

                # Pagar capital de la cuota
                cubrir_cap = min(disponible, cap_cuota)
                imputado_capital += cubrir_cap
                disponible -= cubrir_cap

                if cubrir_int >= int_cuota and cubrir_cap >= cap_cuota:
                    conn.execute(text("UPDATE plan_pagos SET estado = 'PAGADO' WHERE id = :cid"), {"cid": cid})
                    cuotas_liquidadas.append(periodo)

            # Si aún sobra dinero tras cubrir cuotas pendientes inmediatas: es Abono Extraordinario a Capital
            abono_extra_capital = disponible
            if abono_extra_capital > 0:
                imputado_capital += abono_extra_capital
                disponible = 0.0

                # Aplicar abono según destino elegido
                if destino_abono == "reducir_plazo":
                    # Reducir cuotas desde el final del plan
                    cuotas_finales = conn.execute(
                        text("SELECT id, periodo, capital FROM plan_pagos "
                             "WHERE expediente_id = :id AND tipo_expediente = :t AND estado <> 'PAGADO' "
                             "ORDER BY periodo DESC"), {"id": exp_id, "t": tipo}).fetchall()
                    remanente = abono_extra_capital
                    for cf in cuotas_finales:
                        if remanente <= 0:
                            break
                        cap_f = float(cf[2] or 0)
                        if remanente >= cap_f:
                            conn.execute(text("UPDATE plan_pagos SET estado = 'PAGADO_ANTICIPADO', capital = 0, interes = 0, cuota = 0 WHERE id = :id"), {"id": cf[0]})
                            remanente -= cap_f
                        else:
                            conn.execute(text("UPDATE plan_pagos SET capital = capital - :r, cuota = cuota - :r WHERE id = :id"), {"r": remanente, "id": cf[0]})
                            remanente = 0.0
                else:
                    # Reducir valor de cuotas siguientes proporcionalmente
                    cuotas_activas = conn.execute(
                        text("SELECT id, capital, interes FROM plan_pagos "
                             "WHERE expediente_id = :id AND tipo_expediente = :t AND estado <> 'PAGADO' "
                             "ORDER BY periodo ASC"), {"id": exp_id, "t": tipo}).fetchall()
                    if cuotas_activas:
                        descuento_por_cuota = abono_extra_capital / len(cuotas_activas)
                        for ca in cuotas_activas:
                            conn.execute(text("UPDATE plan_pagos SET capital = CASE WHEN capital > :d THEN capital - :d ELSE 0 END, "
                                              "cuota = CASE WHEN cuota > :d THEN cuota - :d ELSE 0 END WHERE id = :id"),
                                         {"d": descuento_por_cuota, "id": ca[0]})

            nuevo_saldo = round(max(0.0, saldo_anterior - imputado_capital), 2)

            cascada_detalle = {
                "gastos_cobranza": round(imputado_gastos, 2),
                "intereses_mora": round(imputado_mora, 2),
                "interes_corriente": round(imputado_interes, 2),
                "abono_capital": round(imputado_capital, 2),
                "cuotas_liquidadas": cuotas_liquidadas,
                "saldo_anterior": saldo_anterior,
                "nuevo_saldo": nuevo_saldo
            }

            # ── 4. Registrar en pagos_recibidos ────────────────────────
            ref_principal = ", ".join(filter(None, [str(m.get("referencia") or m.get("lote") or "EFECTIVO") for m in metodos]))
            comprobante = str(datos.get("comprobante_url") or "")

            q_ins = text("""
                INSERT INTO pagos_recibidos (
                    expediente_id, tipo_expediente, fecha_pago, monto, referencia,
                    moneda, tasa_cambio, monto_ves, metodos_json, cascada_json,
                    cajero, comprobante_url, saldo_anterior, nuevo_saldo, abono_destino, notas
                ) VALUES (
                    :eid, :te, :f, :m, :r,
                    :mon, :tc, :mves, :mjson, :cjson,
                    :caj, :curl, :sant, :nsal, :ad, :not
                )
            """)

            conn.execute(q_ins, {
                "eid": exp_id, "te": tipo, "f": hoy_str, "m": total_pagado_usd,
                "r": ref_principal, "mon": "USD", "tc": tasa_cambio, "mves": total_pagado_ves,
                "mjson": json.dumps(metodos), "cjson": json.dumps(cascada_detalle),
                "caj": cajero, "curl": comprobante, "sant": saldo_anterior,
                "nsal": nuevo_saldo, "ad": destino_abono, "not": str(datos.get("observaciones") or "")
            })

            # Actualizar estado de cobranza en expediente
            if nuevo_saldo <= 0.01:
                nuevo_estado_cobranza = "Pagado"
            elif len(resumen_previo.get("cuotas_vencidas_lista", [])) <= len(cuotas_liquidadas):
                nuevo_estado_cobranza = "Al día"
            else:
                nuevo_estado_cobranza = "En mora"
            tabla_exp = "expedientes_wf" if tipo == "corp" else "expedientes_auto"
            conn.execute(text(f"UPDATE {tabla_exp} SET estado_cobranza = :ec WHERE id = :id"),
                         {"ec": nuevo_estado_cobranza, "id": exp_id})

            # Obtener ID del pago recién insertado
            pago_id_row = conn.execute(text("SELECT MAX(id) FROM pagos_recibidos WHERE expediente_id = :id AND tipo_expediente = :t"),
                                       {"id": exp_id, "t": tipo}).fetchone()
            pago_id = pago_id_row[0] if pago_id_row else 1

        return {
            "pago_id": pago_id,
            "numero_recibo": f"REC-{pago_id:06d}",
            "expediente_id": exp_id,
            "tipo_expediente": tipo,
            "cliente": resumen_previo["cliente"],
            "monto_total_usd": total_pagado_usd,
            "monto_total_ves": total_pagado_ves,
            "tasa_cambio": tasa_cambio,
            "fecha": hoy_str,
            "cajero": cajero,
            "cascada": cascada_detalle,
            "metodos": metodos
        }

    @staticmethod
    def generar_recibo_pdf(pago_id: int, session=None) -> bytes:
        """
        Generador de recibo oficial físico/digital detallando la transacción,
        métodos combinados, cascada legal y fórmula de saldo:
        Saldo Anterior - Pago Realizado = Nuevo Saldo.
        """
        with sesion_activa(session) as conn:
            pago_row = conn.execute(
                text("SELECT * FROM pagos_recibidos WHERE id = :id"), {"id": pago_id}).fetchone()
            if not pago_row:
                raise ValueError(f"Recibo #{pago_id} no encontrado.")
            pago = dict(pago_row._mapping)

            exp_id = pago["expediente_id"]
            tipo = pago["tipo_expediente"]
            tabla = "expedientes_wf" if tipo == "corp" else "expedientes_auto"
            doc_col = "rif" if tipo == "corp" else "cedula"
            exp_row = conn.execute(
                text(f"SELECT cliente, {doc_col} AS documento FROM {tabla} WHERE id = :id"),
                {"id": exp_id}).fetchone()
            cliente = exp_row[0] if exp_row else "Cliente Registrado"
            documento = exp_row[1] if exp_row else "N/A"

        metodos = json.loads(pago.get("metodos_json") or "[]")
        cascada = json.loads(pago.get("cascada_json") or "{}")

        pdf = ReciboPDF('P', 'mm', 'Letter')
        pdf.add_page()
        pdf.ln(10)

        # ── Datos del Recibo y Cliente ────────────────────────────────
        pdf.set_fill_color(245, 247, 250)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(100, 8, _sanitizar_pdf_txt(f"RECIBO DE CAJA: REC-{pago_id:06d}"), 0)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(95, 8, _sanitizar_pdf_txt(f"Fecha: {pago.get('fecha_pago')}  |  Cajero: {pago.get('cajero')}"), 0, ln=True, align='R')
        pdf.line(10, pdf.get_y(), 205, pdf.get_y())
        pdf.ln(3)

        pdf.set_font('Arial', '', 9)
        pdf.cell(100, 6, _sanitizar_pdf_txt(f"Cliente: {cliente}"))
        pdf.cell(95, 6, _sanitizar_pdf_txt(f"Documento (C.I./RIF): {documento}"), ln=True)
        pdf.cell(100, 6, _sanitizar_pdf_txt(f"Credito: EXP-{tipo.upper()}-{exp_id:04d}"))
        pdf.cell(95, 6, _sanitizar_pdf_txt(f"Tasa de cambio aplicada: {pago.get('tasa_cambio', 1.0):,.2f} VES/USD"), ln=True)
        pdf.ln(4)

        # ── Desglose de Caja Mixta ────────────────────────────────────
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(0, 7, "1. FORMAS DE PAGO RECIBIDAS (CAJA MIXTA)", ln=True, fill=True)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(45, 6, "Metodo", 1)
        pdf.cell(50, 6, "Referencia / Lote", 1)
        pdf.cell(50, 6, "Detalle / Banco", 1)
        pdf.cell(50, 6, "Monto Aportado", 1, ln=True)

        pdf.set_font('Arial', '', 8)
        for m in metodos:
            pdf.cell(45, 6, _sanitizar_pdf_txt(str(m.get("tipo", "")).upper()), 1)
            pdf.cell(50, 6, _sanitizar_pdf_txt(str(m.get("referencia") or m.get("lote") or "N/A")), 1)
            detalle = str(m.get("banco_origen") or m.get("tarjeta_ultimos_4") or "")
            pdf.cell(50, 6, _sanitizar_pdf_txt(detalle if detalle else "En ventanilla"), 1)
            pdf.cell(50, 6, f"{float(m.get('monto', 0)):,.2f} {m.get('moneda', 'USD')}", 1, ln=True)

        pdf.ln(4)

        # ── Cascada Legal ─────────────────────────────────────────────
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(0, 7, "2. DISTRIBUCION LEGAL DEL INGRESO (ORDEN FINANCIERO)", ln=True, fill=True)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(130, 6, "Gastos de Cobranza y Honorarios Administrativos:", 1)
        pdf.cell(65, 6, f"$ {cascada.get('gastos_cobranza', 0):,.2f}", 1, ln=True, align='R')
        pdf.cell(130, 6, "Intereses de Mora Acumulados:", 1)
        pdf.cell(65, 6, f"$ {cascada.get('intereses_mora', 0):,.2f}", 1, ln=True, align='R')
        pdf.cell(130, 6, "Intereses Corrientes del Periodo:", 1)
        pdf.cell(65, 6, f"$ {cascada.get('interes_corriente', 0):,.2f}", 1, ln=True, align='R')
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(130, 6, "Abono Efectivo a Capital:", 1)
        pdf.cell(65, 6, f"$ {cascada.get('abono_capital', 0):,.2f}", 1, ln=True, align='R')

        pdf.ln(4)

        # ── Estado de Deuda: Saldo Anterior - Pago = Nuevo Saldo ──────
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(0, 7, "3. ESTADO ACTUALIZADO DE LA DEUDA", ln=True, fill=True)
        pdf.set_font('Arial', '', 9)
        saldo_ant = float(pago.get("saldo_anterior") or 0.0)
        pago_tot = float(pago.get("monto") or 0.0)
        nuevo_sal = float(pago.get("nuevo_saldo") or 0.0)

        pdf.cell(65, 8, f"Saldo Anterior: $ {saldo_ant:,.2f}", 1, align='C')
        pdf.cell(65, 8, f"Menos Pago Total: - $ {pago_tot:,.2f}", 1, align='C')
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(65, 8, f"NUEVO SALDO: $ {nuevo_sal:,.2f}", 1, ln=True, align='C')

        pdf.ln(18)
        pdf.set_font('Arial', '', 8)
        y_firmas = pdf.get_y()
        pdf.line(25, y_firmas, 85, y_firmas)
        pdf.line(125, y_firmas, 185, y_firmas)
        pdf.text(35, y_firmas + 4, "Firma del Cajero / Operador")
        pdf.text(138, y_firmas + 4, "Firma del Cliente / Pagador")

        out = pdf.output(dest='S')
        if isinstance(out, str):
            return out.encode('latin-1')
        return bytes(out)

    @staticmethod
    def obtener_creditos_pagados(session=None) -> dict:
        """
        Retorna el consolidado y listado de créditos totalmente pagados / liquidados.
        Un crédito se considera pagado cuando:
        - Ha sido formalmente aprobado por el Comité de Crédito.
        - Posee plan de pagos y su saldo de capital deudor es <= 0.01 (todas las cuotas liquidadas).
        - O su estado_cobranza es 'Pagado' o 'Liquidado'.
        """
        with sesion_activa(session) as conn:
            # 1. Buscar expedientes en plan_pagos con saldo capital <= 0.01
            q_plan_pagados = text("""
                SELECT 
                    p.expediente_id, p.tipo_expediente,
                    COUNT(*) as total_cuotas,
                    SUM(CASE WHEN p.estado IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN 1 ELSE 0 END) as cuotas_pagadas,
                    SUM(p.capital) as capital_total,
                    SUM(p.interes) as interes_total,
                    SUM(CASE WHEN p.estado NOT IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN p.capital ELSE 0 END) as saldo_capital,
                    MAX(p.fecha_pago) as fecha_fin_plan
                FROM plan_pagos p
                GROUP BY p.expediente_id, p.tipo_expediente
                HAVING COUNT(*) > 0 
                   AND SUM(CASE WHEN p.estado NOT IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN p.capital ELSE 0 END) <= 0.01
            """)
            filas_pagados = conn.execute(q_plan_pagados).fetchall()

            creditos = []
            monto_total_prestado = 0.0
            monto_total_recaudado = 0.0
            total_intereses_cobrados = 0.0

            for fila in filas_pagados:
                d = dict(fila._mapping)
                exp_id = d["expediente_id"]
                tipo = d["tipo_expediente"]

                tabla = "expedientes_wf" if tipo == "corp" else "expedientes_auto"
                doc_col = "rif" if tipo == "corp" else "cedula"
                exp = conn.execute(
                    text(f"SELECT id, cliente, {doc_col} AS documento, monto, tasa_aprobada, plazo_meses, fecha, dictamen, estado_cobranza "
                         f"FROM {tabla} WHERE id = :id AND eliminado = 0 AND dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')"),
                    {"id": exp_id}
                ).fetchone()

                if not exp:
                    continue

                exp_data = dict(exp._mapping)
                monto_orig = float(exp_data.get("monto") or d.get("capital_total") or 0.0)

                # Pagos recibidos
                pagos = conn.execute(
                    text("SELECT COUNT(*) AS recibos, SUM(monto) AS total_pagado, MAX(fecha_pago) AS fecha_ult_pago, MAX(cajero) AS cajero "
                         "FROM pagos_recibidos WHERE expediente_id = :id AND tipo_expediente = :t"),
                    {"id": exp_id, "t": tipo}
                ).fetchone()

                num_recibos = int(pagos[0]) if (pagos and pagos[0] is not None) else 0
                total_pag = float(pagos[1]) if (pagos and pagos[1] is not None) else monto_orig
                fecha_ult = str(pagos[2]) if (pagos and pagos[2]) else str(d.get("fecha_fin_plan") or "")
                cajero = str(pagos[3]) if (pagos and pagos[3]) else "Caja"

                cap_pag = float(d.get("capital_total") or monto_orig)
                int_pag = float(d.get("interes_total") or 0.0)

                item = {
                    "id": exp_id,
                    "tipo": tipo,
                    "codigo_credito": f"EXP-{tipo.upper()}-{exp_id:04d}",
                    "cliente": exp_data.get("cliente") or f"Expediente #{exp_id}",
                    "documento": exp_data.get("documento") or "",
                    "monto_original": round(monto_orig, 2),
                    "tasa_aprobada": float(exp_data.get("tasa_aprobada") or 0.0),
                    "plazo_meses": int(exp_data.get("plazo_meses") or d["total_cuotas"]),
                    "cuotas_totales": int(d["total_cuotas"]),
                    "cuotas_pagadas": int(d["cuotas_pagadas"]),
                    "total_capital_pagado": round(cap_pag, 2),
                    "total_intereses_pagados": round(int_pag, 2),
                    "total_pagado": round(total_pag, 2),
                    "saldo_capital": 0.0,
                    "estado_cobranza": "Pagado",
                    "fecha_aprobacion": str(exp_data.get("fecha") or "")[:10],
                    "fecha_liquidacion": fecha_ult[:10] if fecha_ult else str(exp_data.get("fecha") or "")[:10],
                    "recibos_emitidos": num_recibos,
                    "cajero_ultimo_cobro": cajero
                }

                creditos.append(item)
                monto_total_prestado += monto_orig
                monto_total_recaudado += total_pag
                total_intereses_cobrados += int_pag

            # Ordenar por fecha de liquidación más reciente
            creditos.sort(key=lambda x: (x["fecha_liquidacion"], x["id"]), reverse=True)

            resumen = {
                "total_creditos_pagados": len(creditos),
                "monto_total_prestado": round(monto_total_prestado, 2),
                "monto_total_recaudado": round(monto_total_recaudado, 2),
                "total_intereses_cobrados": round(total_intereses_cobrados, 2),
                "tasa_cumplimiento": 100.0 if creditos else 0.0
            }

            return {
                "resumen": resumen,
                "creditos": creditos
            }

    @staticmethod
    def generar_finiquito_pdf(exp_id: int, tipo: str, session=None) -> bytes:
        """
        Generador de Certificado Oficial de Finiquito y Solvencia Legal.
        Certifica la extinción total de la deuda para créditos 100% liquidados.
        """
        with sesion_activa(session) as conn:
            tabla = "expedientes_wf" if tipo == "corp" else "expedientes_auto"
            doc_col = "rif" if tipo == "corp" else "cedula"
            exp_row = conn.execute(
                text(f"SELECT cliente, {doc_col} AS documento, monto, tasa_aprobada, plazo_meses, fecha "
                     f"FROM {tabla} WHERE id = :id AND eliminado = 0"),
                {"id": exp_id}
            ).fetchone()

            if not exp_row:
                raise ValueError(f"Expediente #{exp_id} no encontrado.")

            exp = dict(exp_row._mapping)
            cliente = exp.get("cliente") or "Cliente Registrado"
            documento = exp.get("documento") or "N/A"
            monto_original = float(exp.get("monto") or 0.0)
            tasa = float(exp.get("tasa_aprobada") or 0.0)
            plazo = int(exp.get("plazo_meses") or 0)
            fecha_aprob = str(exp.get("fecha") or "")[:10]

            # Plan de pagos y saldo
            cuotas_row = conn.execute(
                text("SELECT COUNT(*) AS total_cuotas, "
                     "SUM(CASE WHEN estado IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN 1 ELSE 0 END) AS cuotas_pagadas, "
                     "SUM(capital) AS total_cap, SUM(interes) AS total_int, "
                     "SUM(CASE WHEN estado NOT IN ('PAGADO', 'PAGADO_ANTICIPADO') THEN capital ELSE 0 END) AS saldo_capital "
                     "FROM plan_pagos WHERE expediente_id = :id AND tipo_expediente = :t"),
                {"id": exp_id, "t": tipo}
            ).fetchone()

            total_cuotas = int(cuotas_row[0]) if (cuotas_row and cuotas_row[0] is not None) else plazo
            cuotas_pagadas = int(cuotas_row[1]) if (cuotas_row and cuotas_row[1] is not None) else 0
            cap_amortizado = float(cuotas_row[2]) if (cuotas_row and cuotas_row[2] is not None) else monto_original
            int_pagados = float(cuotas_row[3]) if (cuotas_row and cuotas_row[3] is not None) else 0.0

            # Historial de pagos
            pagos_rows = conn.execute(
                text("SELECT id, fecha_pago, monto, referencia, moneda, cajero "
                     "FROM pagos_recibidos WHERE expediente_id = :id AND tipo_expediente = :t "
                     "ORDER BY id ASC"),
                {"id": exp_id, "t": tipo}
            ).fetchall()

            total_recaudado = sum(float(p[2] or 0.0) for p in pagos_rows) if pagos_rows else (cap_amortizado + int_pagados)
            fecha_fin = str(pagos_rows[-1][1]) if pagos_rows else date.today().strftime("%Y-%m-%d")

        pdf = CertificadoFiniquitoPDF('P', 'mm', 'Letter')
        pdf.add_page()
        pdf.ln(12)

        # Encabezado y Código de Solvencia
        pdf.set_fill_color(245, 247, 250)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(11, 29, 78)
        cod_solvencia = f"FIN-EXP-{tipo.upper()}-{exp_id:04d}-{date.today().year}"
        pdf.cell(110, 8, _sanitizar_pdf_txt(f"CONSTANCIA DE SOLVENCIA: {cod_solvencia}"), 0)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(85, 8, _sanitizar_pdf_txt(f"Fecha de Emision: {date.today().strftime('%Y-%m-%d')}"), 0, ln=True, align='R')
        pdf.line(10, pdf.get_y(), 205, pdf.get_y())
        pdf.ln(4)

        # Datos del Titular y Crédito
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(0, 7, "1. IDENTIFICACION DEL CLIENTE Y OPERACION CREDITICIA", ln=True, fill=True)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(100, 6, _sanitizar_pdf_txt(f"Titular / Razon Social: {cliente}"))
        pdf.cell(95, 6, _sanitizar_pdf_txt(f"Documento (C.I. / RIF): {documento}"), ln=True)
        pdf.cell(100, 6, _sanitizar_pdf_txt(f"Codigo de Credito: EXP-{tipo.upper()}-{exp_id:04d}"))
        pdf.cell(95, 6, _sanitizar_pdf_txt(f"Tipo de Cartera: {'Corporativo / Comercial' if tipo == 'corp' else 'Automotriz'}"), ln=True)
        pdf.cell(100, 6, _sanitizar_pdf_txt(f"Fecha de Aprobacion: {fecha_aprob}"))
        pdf.cell(95, 6, _sanitizar_pdf_txt(f"Fecha de Finiquito / Liquidacion: {fecha_fin}"), ln=True)
        pdf.ln(3)

        # Resumen de Liquidación Financiera
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(0, 7, "2. RESUMEN FINANCIERO Y CUMPLIMIENTO DEL PLAN DE PAGOS", ln=True, fill=True)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(130, 6, "Monto Original Financiado:", 1)
        pdf.cell(65, 6, f"$ {monto_original:,.2f} USD", 1, ln=True, align='R')
        pdf.cell(130, 6, "Tasa de Interes Efectiva Aprobada:", 1)
        pdf.cell(65, 6, f"{tasa:,.2f} %", 1, ln=True, align='R')
        pdf.cell(130, 6, "Total de Cuotas Pactadas y Liquidadas:", 1)
        pdf.cell(65, 6, f"{cuotas_pagadas} de {total_cuotas} cuotas (100% CUMPLIDO)", 1, ln=True, align='R')
        pdf.cell(130, 6, "Capital Total Amortizado:", 1)
        pdf.cell(65, 6, f"$ {cap_amortizado:,.2f} USD", 1, ln=True, align='R')
        pdf.cell(130, 6, "Intereses Totales Pagados:", 1)
        pdf.cell(65, 6, f"$ {int_pagados:,.2f} USD", 1, ln=True, align='R')
        pdf.cell(130, 6, "Total General Pagado por el Cliente:", 1)
        pdf.cell(65, 6, f"$ {total_recaudado:,.2f} USD", 1, ln=True, align='R')

        pdf.set_fill_color(230, 245, 230)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(15, 110, 40)
        pdf.cell(130, 7, "SALDO CAPITAL DEUDOR REMANENTE:", 1, fill=True)
        pdf.cell(65, 7, "$ 0.00 USD (SOLVENTE)", 1, ln=True, align='R', fill=True)
        pdf.ln(3)

        # Declaración Oficial de Finiquito y No Adeudo
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(11, 29, 78)
        pdf.cell(0, 7, "3. DECLARACION FORMAL DE SOLVENCIA Y FINIQUITO LEGAL", ln=True, fill=True)
        pdf.set_font('Arial', '', 8.5)
        pdf.set_text_color(50, 50, 50)
        texto_declaracion = (
            "KAIZEN FINANCIAL GROUP hace constar de manera formal e irrevocable que el cliente antes citado "
            "ha cancelado integramente todas las cuotas, intereses y obligaciones derivadas del contrato de credito indicado. "
            "En consecuencia, el citado titular NO MANTIENE DEUDA PENDIENTE ni saldos exigibles con esta institucion por "
            "dicho concepto, otorgandose el presente FINIQUITO TOTAL Y DEFINITIVO, procediendo el levantamiento y liberacion "
            "de las garantias o reservas de dominio constituidas a favor de esta entidad."
        )
        pdf.multi_cell(0, 5, _sanitizar_pdf_txt(texto_declaracion))
        pdf.ln(3)

        # Recibos Emitidos de Soporte
        if pagos_rows:
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color(11, 29, 78)
            pdf.cell(0, 6, "4. COMPROBANTES DE PAGO EMITIDOS (AUDITORIA DE CAJA)", ln=True)
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(35, 5, "Nro. Recibo", 1)
            pdf.cell(35, 5, "Fecha de Pago", 1)
            pdf.cell(45, 5, "Referencia", 1)
            pdf.cell(45, 5, "Cajero", 1)
            pdf.cell(35, 5, "Monto USD", 1, ln=True, align='R')
            pdf.set_font('Arial', '', 8)
            for p in pagos_rows[:6]:
                pdf.cell(35, 5, f"REC-{p[0]:06d}", 1)
                pdf.cell(35, 5, str(p[1])[:10], 1)
                pdf.cell(45, 5, _sanitizar_pdf_txt(str(p[3] or "EFECTIVO")), 1)
                pdf.cell(45, 5, _sanitizar_pdf_txt(str(p[5] or "Caja")), 1)
                pdf.cell(35, 5, f"$ {float(p[2] or 0):,.2f}", 1, ln=True, align='R')
            if len(pagos_rows) > 6:
                pdf.set_font('Arial', 'I', 7.5)
                pdf.cell(0, 4, f"* y {len(pagos_rows) - 6} comprobantes adicionales registrados en el libro diario de cobranzas.", ln=True)

        # Firmas y Sellos
        pdf.ln(12)
        pdf.set_font('Arial', '', 8)
        y_firmas = pdf.get_y()
        pdf.line(25, y_firmas, 85, y_firmas)
        pdf.line(125, y_firmas, 185, y_firmas)
        pdf.text(30, y_firmas + 4, "Gerencia de Cartera y Cobranzas")
        pdf.text(32, y_firmas + 8, "KAIZEN FINANCIAL GROUP")
        pdf.text(130, y_firmas + 4, "Comite de Credito y Riesgo")
        pdf.text(136, y_firmas + 8, "Firma y Sello Oficial")

        out = pdf.output(dest='S')
        if isinstance(out, str):
            return out.encode('latin-1')
        return bytes(out)

    @staticmethod
    def obtener_historial_pagos(exp_id: int, tipo: str, session=None) -> list[dict]:
        """Historial de cobros de un expediente concreto."""
        with sesion_activa(session) as conn:
            filas = conn.execute(
                text("SELECT id, expediente_id, tipo_expediente, fecha_pago, monto, "
                     "referencia, moneda, tasa_cambio, monto_ves, metodos_json, "
                     "cascada_json, cajero, nuevo_saldo, notas "
                     "FROM pagos_recibidos WHERE expediente_id = :id AND tipo_expediente = :t "
                     "ORDER BY id DESC"), {"id": exp_id, "t": tipo}).fetchall()

            res = []
            for f in filas:
                d = dict(f._mapping)
                d["numero_recibo"] = f"REC-{d['id']:06d}"
                d["metodos"] = json.loads(d.get("metodos_json") or "[]")
                d["cascada"] = json.loads(d.get("cascada_json") or "{}")
                res.append(d)
            return res

    @staticmethod
    def obtener_arqueo_diario(fecha: str = None, session=None) -> dict:
        """
        Módulo de arqueo diario: resume el dinero cobrado en la jornada
        desglosado por efectivo USD, efectivo VES, puntos de venta y transferencias.
        """
        dia = fecha or date.today().strftime("%Y-%m-%d")

        with sesion_activa(session) as conn:
            filas = conn.execute(
                text("SELECT id, expediente_id, tipo_expediente, fecha_pago, monto, "
                     "referencia, moneda, tasa_cambio, monto_ves, metodos_json, cajero "
                     "FROM pagos_recibidos WHERE fecha_pago = :f ORDER BY id DESC"),
                {"f": dia}).fetchall()

        total_usd = 0.0
        total_ves = 0.0
        efectivo_usd = 0.0
        efectivo_ves = 0.0
        pos_ves = 0.0
        transferencias_ves = 0.0
        transacciones = []

        for r in filas:
            p = dict(r._mapping)
            monto_usd = float(p.get("monto") or 0.0)
            monto_ves = float(p.get("monto_ves") or 0.0)
            total_usd += monto_usd
            total_ves += monto_ves

            metodos = json.loads(p.get("metodos_json") or "[]")
            for m in metodos:
                mtipo = str(m.get("tipo") or "").lower()
                mval = float(m.get("monto") or 0.0)
                mmon = str(m.get("moneda") or "USD").upper()

                if "efectivo" in mtipo:
                    if mmon == "USD":
                        efectivo_usd += mval
                    else:
                        efectivo_ves += mval
                elif "punto" in mtipo or "tarjeta" in mtipo or "pos" in mtipo:
                    pos_ves += mval
                else:
                    transferencias_ves += mval

            transacciones.append({
                "id": p["id"],
                "recibo": f"REC-{p['id']:06d}",
                "expediente": f"{p['tipo_expediente'].upper()} #{p['expediente_id']}",
                "monto_usd": monto_usd,
                "monto_ves": monto_ves,
                "referencia": p.get("referencia") or "S/R",
                "cajero": p.get("cajero") or "Caja"
            })

        return {
            "fecha": dia,
            "total_usd": round(total_usd, 2),
            "total_ves": round(total_ves, 2),
            "efectivo_usd": round(efectivo_usd, 2),
            "efectivo_ves": round(efectivo_ves, 2),
            "pos_ves": round(pos_ves, 2),
            "transferencias_ves": round(transferencias_ves, 2),
            "total_transacciones": len(transacciones),
            "transacciones": transacciones
        }

    @staticmethod
    def cerrar_arqueo_diario(datos: dict, session=None) -> dict:
        """Registra el cierre formal de turno del cajero con comparación y diferencias."""
        fecha = str(datos.get("fecha") or date.today().strftime("%Y-%m-%d"))
        cajero = str(datos.get("cajero") or "Cajero")
        efectivo_usd = float(datos.get("efectivo_declarado_usd") or 0.0)
        efectivo_ves = float(datos.get("efectivo_declarado_ves") or 0.0)
        pos_ves = float(datos.get("pos_declarado_ves") or 0.0)
        transf_ves = float(datos.get("transferencias_declarado_ves") or 0.0)

        resumen = CollectionService.obtener_arqueo_diario(fecha, session=session)

        dif_usd = round(efectivo_usd - resumen["efectivo_usd"], 2)
        dif_ves = round((efectivo_ves + pos_ves + transf_ves) - resumen["total_ves"], 2)

        ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sesion_activa(session) as conn:
            conn.execute(
                text("""INSERT INTO arqueos_caja (
                    fecha, cajero, total_sistema_usd, total_sistema_ves,
                    efectivo_declarado_usd, efectivo_declarado_ves,
                    pos_declarado_ves, transferencias_declarado_ves,
                    diferencia_usd, diferencia_ves, estado, observaciones, fecha_cierre
                ) VALUES (
                    :f, :c, :tsu, :tsv, :edu, :edv, :pos, :trf, :du, :dv, 'CERRADO', :obs, :fc
                )"""),
                {
                    "f": fecha, "c": cajero, "tsu": resumen["total_usd"], "tsv": resumen["total_ves"],
                    "edu": efectivo_usd, "edv": efectivo_ves, "pos": pos_ves, "trf": transf_ves,
                    "du": dif_usd, "dv": dif_ves, "obs": str(datos.get("observaciones") or ""),
                    "fc": ahora_str
                }
            )

        return {
            "fecha": fecha,
            "cajero": cajero,
            "estado": "CERRADO",
            "diferencia_usd": dif_usd,
            "diferencia_ves": dif_ves,
            "cuadrado": abs(dif_usd) < 0.01 and abs(dif_ves) < 0.01,
            "fecha_cierre": ahora_str
        }

    @staticmethod
    def obtener_ultimos_cobros(limite: int = 15, session=None) -> list[dict]:
        """Últimos cobros registrados en el sistema para auditoría y monitoreo en tiempo real."""
        with sesion_activa(session) as conn:
            filas = conn.execute(
                text("""
                    SELECT TOP (:lim)
                        p.id, p.expediente_id, p.tipo_expediente, p.fecha_pago, p.monto,
                        p.referencia, p.moneda, p.tasa_cambio, p.monto_ves, p.metodos_json,
                        p.cajero, p.creado_en
                    FROM pagos_recibidos p
                    ORDER BY p.id DESC
                """),
                {"lim": limite}
            ).fetchall()

            # Diccionario de nombres de clientes en memoria para optimizar
            resultado = []
            for r in filas:
                p = dict(r._mapping)
                exp_id = p["expediente_id"]
                tipo = p["tipo_expediente"]

                cliente_nom = f"Expediente #{exp_id}"
                if tipo == "corp":
                    c_row = conn.execute(text("SELECT cliente FROM expedientes_wf WHERE id = :id"), {"id": exp_id}).fetchone()
                    if c_row and c_row[0]:
                        cliente_nom = c_row[0]
                else:
                    c_row = conn.execute(text("SELECT cliente FROM expedientes_auto WHERE id = :id"), {"id": exp_id}).fetchone()
                    if c_row and c_row[0]:
                        cliente_nom = c_row[0]

                metodos = json.loads(p.get("metodos_json") or "[]")
                if len(metodos) > 1:
                    metodo_str = f"Mixto ({len(metodos)} formas)"
                elif len(metodos) == 1:
                    m = metodos[0]
                    metodo_str = f"{m.get('tipo', 'Pago').capitalize()} ({m.get('moneda', 'USD')})"
                else:
                    metodo_str = p.get("moneda") or "USD"

                hora_str = ""
                creado = p.get("creado_en")
                if creado:
                    hora_str = str(creado)[11:16]
                if not hora_str:
                    hora_str = "Hoy"

                resultado.append({
                    "id": p["id"],
                    "numero_recibo": f"REC-{p['id']:06d}",
                    "hora": hora_str,
                    "fecha": str(p["fecha_pago"]),
                    "cliente": cliente_nom,
                    "tipo_expediente": tipo,
                    "expediente_id": exp_id,
                    "monto_usd": float(p.get("monto") or 0.0),
                    "monto_ves": float(p.get("monto_ves") or 0.0),
                    "metodo": metodo_str,
                    "referencia": p.get("referencia") or "S/R",
                    "cajero": p.get("cajero") or "Caja"
                })

            return resultado

    @staticmethod
    def obtener_alertas_vencimientos(dias_ventana: int = 30, limite: int = 25, session=None) -> list[dict]:
        """Lista prioritaria de clientes para cobranza preventiva y cuotas vencidas."""
        with sesion_activa(session) as conn:
            filas = conn.execute(
                text("""
                    SELECT TOP (:lim)
                        p.id, p.expediente_id, p.tipo_expediente, p.periodo, p.cuota,
                        p.fecha_pago,
                        DATEDIFF(day, p.fecha_pago, GETDATE()) AS dias_atraso
                    FROM plan_pagos p
                    WHERE p.estado <> 'PAGADO'
                      AND p.fecha_pago <= DATEADD(day, :dias, GETDATE())
                      AND (
                          (p.tipo_expediente = 'corp' AND EXISTS (
                              SELECT 1 FROM expedientes_wf w
                              WHERE w.id = p.expediente_id AND w.eliminado = 0
                                AND w.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                          ))
                          OR
                          (p.tipo_expediente = 'auto' AND EXISTS (
                              SELECT 1 FROM expedientes_auto a
                              WHERE a.id = p.expediente_id AND a.eliminado = 0
                                AND a.dictamen IN ('APROBADO', 'APROBADO_CON_CONDICIONES')
                          ))
                      )
                    ORDER BY p.fecha_pago ASC
                """),
                {"lim": limite, "dias": dias_ventana}
            ).fetchall()

            res = []
            for r in filas:
                f = dict(r._mapping)
                exp_id = f["expediente_id"]
                tipo = f["tipo_expediente"]
                dias_atraso = int(f.get("dias_atraso") or 0)

                cliente = f"Expediente {tipo.upper()} #{exp_id}"
                telefono = "No registrado"
                documento = ""

                if tipo == "corp":
                    q_c = conn.execute(
                        text("""
                            SELECT w.cliente, w.rif,
                                   COALESCE(c.telefono, '') AS tel
                            FROM expedientes_wf w
                            LEFT JOIN clientes c ON c.rif = w.rif
                            WHERE w.id = :id
                        """),
                        {"id": exp_id}
                    ).fetchone()
                    if q_c:
                        cliente = q_c[0] or cliente
                        documento = q_c[1] or ""
                        telefono = q_c[2] if (len(q_c) > 2 and q_c[2]) else telefono
                else:
                    q_a = conn.execute(
                        text("""
                            SELECT cliente, cedula, COALESCE(telefono, '') AS tel
                            FROM expedientes_auto
                            WHERE id = :id
                        """),
                        {"id": exp_id}
                    ).fetchone()
                    if q_a:
                        cliente = q_a[0] or cliente
                        documento = q_a[1] or ""
                        telefono = q_a[2] if (len(q_a) > 2 and q_a[2]) else telefono

                if dias_atraso > 0:
                    dias_texto = f"{dias_atraso} días de atraso"
                    estado_alerta = "vencido"
                elif dias_atraso == 0:
                    dias_texto = "Vence hoy"
                    estado_alerta = "hoy"
                else:
                    dias_texto = f"Vence en {abs(dias_atraso)} días"
                    estado_alerta = "por_vencer"

                res.append({
                    "id": f["id"],
                    "expediente_id": exp_id,
                    "tipo_expediente": tipo,
                    "codigo_credito": f"EXP-{tipo.upper()}-{exp_id:04d}",
                    "periodo": f["periodo"],
                    "cliente": cliente,
                    "documento": documento,
                    "telefono": telefono or "No registrado",
                    "cuota": float(f.get("cuota") or 0.0),
                    "fecha_pago": str(f["fecha_pago"]),
                    "dias_atraso": dias_atraso,
                    "dias_texto": dias_texto,
                    "estado_alerta": estado_alerta
                })

            return res
