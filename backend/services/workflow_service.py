"""
Reglas del circuito de evaluación crediticia.

Aquí viven las guardas que antes estaban incrustadas en los DAOs. La capa de
datos vuelve así a hacer solo lo suyo —leer y escribir— y este servicio queda
como único punto donde se decide si una transición es legítima, tanto para la
interfaz de Streamlit como para las rutas de la API.

Las excepciones son de dominio, no de HTTP: cada consumidor las traduce a lo
suyo. Las rutas las mapean a 404 y 409; la interfaz las muestra como aviso.
"""

from datetime import datetime

from database.daos_sqlserver import (ExpedienteAutomotrizDAO, ExpedienteCorporativoDAO,
                                     TareaWorkflowDAO, WorkflowCumplimientoDAO,
                                     EW_CREDITO_LEGAL, EW_CUMPLIMIENTO,
                                     EW_RECHAZADO_COMP, EW_SUBSANACION)
from database.db_core_sqlserver import sesion_activa

TIPOS_VALIDOS = ('corp', 'auto')


class ErrorFlujo(Exception):
    """Raíz de los errores de negocio del circuito."""


class ExpedienteNoEncontrado(ErrorFlujo):
    """El expediente no existe o está dado de baja lógica."""


class TransicionInvalida(ErrorFlujo):
    """La transición solicitada no es legítima en el estado actual."""


class DatosInsuficientes(ErrorFlujo):
    """Falta información obligatoria para registrar la transición."""


def _dao(tipo):
    if tipo not in TIPOS_VALIDOS:
        raise DatosInsuficientes(
            f"Tipo de expediente no reconocido: {tipo!r}. Use 'corp' o 'auto'.")
    return ExpedienteCorporativoDAO if tipo == 'corp' else ExpedienteAutomotrizDAO


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class WorkflowService:
    """Transiciones del expediente, con sus reglas aplicadas antes de escribir."""

    # ── Consultas ─────────────────────────────────────────────────────
    @staticmethod
    def obtener(exp_id, tipo, session=None):
        """
        Expediente por id, o `ExpedienteNoEncontrado` si no existe.

        Centraliza la comprobación para que ninguna transición escriba sobre un
        expediente inexistente.
        """
        registro = _dao(tipo).get_by_id(exp_id, session=session)
        if not registro:
            raise ExpedienteNoEncontrado(
                f"No existe el expediente {tipo}/{exp_id} o fue eliminado.")
        return registro

    @staticmethod
    def estado(exp_id, tipo, session=None):
        """Estado del flujo, dictamen y firmas del expediente."""
        WorkflowService.obtener(exp_id, tipo, session=session)
        return WorkflowCumplimientoDAO.get_estado(exp_id, tipo, session=session)

    @staticmethod
    def tareas(exp_id, tipo, estado=None, session=None):
        """Tareas del expediente, opcionalmente filtradas por estado."""
        WorkflowService.obtener(exp_id, tipo, session=session)
        return TareaWorkflowDAO.get_por_expediente(exp_id, tipo, estado=estado,
                                                   session=session)

    # ── Guardas ───────────────────────────────────────────────────────
    @staticmethod
    def exigir_cumplimiento(exp_id, tipo, session=None):
        """
        Cumplimiento es la primera revisión formal: sin su certificación el
        expediente no puede alcanzar Crédito, Legal ni Comité.

        Raises:
            ExpedienteNoEncontrado: si el expediente no existe.
            TransicionInvalida: si Cumplimiento aún no ha firmado.
        """
        registro = WorkflowService.obtener(exp_id, tipo, session=session)
        if registro.get('status_comp') != 1:
            raise TransicionInvalida(
                "El expediente no puede avanzar: Cumplimiento es la primera "
                "revisión formal y todavía no ha certificado.")
        return registro

    @staticmethod
    def exigir_editable(exp_id, tipo, session=None):
        """
        El expediente admite cambios mientras el Comité no se haya pronunciado.

        Con dictamen firme, lo registrado es la base de una decisión tomada:
        reescribirlo dejaría un expediente que ya no dice lo que se evaluó. La
        vía para rehacerlo es la reevaluación, que abre un expediente nuevo.

        Raises:
            ExpedienteNoEncontrado: si el expediente no existe.
            TransicionInvalida: si ya tiene dictamen de aprobación o rechazo.
        """
        registro = WorkflowService.obtener(exp_id, tipo, session=session)
        if registro.get('dictamen') in ('APROBADO', 'RECHAZADO'):
            raise TransicionInvalida(
                "El expediente ya tiene dictamen {0}: no admite cambios.".format(
                    registro['dictamen']))
        return registro

    @staticmethod
    def exigir_firmas_completas(exp_id, tipo, session=None):
        """Las tres firmas deben estar registradas antes de la decisión final."""
        registro = WorkflowService.obtener(exp_id, tipo, session=session)
        faltan = [nombre for nombre, campo in
                  (('Cumplimiento', 'status_comp'), ('Legal', 'status_leg'),
                   ('Riesgo', 'status_riesgo'))
                  if registro.get(campo) != 1]
        if faltan:
            raise TransicionInvalida(
                "No se puede emitir el dictamen: faltan las firmas de "
                + ", ".join(faltan) + ".")
        return registro

    @staticmethod
    def _exigir_texto(valor, mensaje):
        if not str(valor or "").strip():
            raise DatosInsuficientes(mensaje)
        return str(valor).strip()

    # ── Etapa de Cumplimiento ─────────────────────────────────────────
    @staticmethod
    def certificar_cumplimiento(exp_id, tipo, usuario='', datos=None, session=None):
        """
        Cierra Cumplimiento y abre de golpe Crédito y Legal Fase 1.

        Returns:
            dict con el estado resultante y el número de tareas abiertas.
        """
        with sesion_activa(session) as s:
            registro = WorkflowService.obtener(exp_id, tipo, session=s)
            if registro.get('status_comp') == 1:
                raise TransicionInvalida(
                    "El expediente ya fue certificado por Cumplimiento.")
            if str(registro.get('dictamen', '')).upper() in ('APROBADO', 'RECHAZADO'):
                raise TransicionInvalida(
                    "El expediente está cerrado y no admite nuevas certificaciones.")

            # La UI captura los datos AML/CFT en la misma acción que firma la
            # etapa. El servicio los persiste dentro de la misma transacción
            # para que ninguna vista tenga que alterar el estado directamente.
            if datos is not None:
                try:
                    _dao(tipo).update_compliance(exp_id=exp_id, session=s, **datos)
                except TypeError as error:
                    raise DatosInsuficientes(
                        f"Los datos de Cumplimiento no son válidos: {error}") from error

            n = WorkflowCumplimientoDAO.certificar(
                exp_id, tipo, usuario=usuario, fecha=_ahora(), session=s)
        return {"expediente_id": exp_id, "tipo": tipo,
                "estado_workflow": EW_CREDITO_LEGAL, "tareas_abiertas": n}

    @staticmethod
    def observar(exp_id, tipo, observaciones, usuario='', session=None):
        """Devuelve el expediente al área comercial para subsanación."""
        obs = WorkflowService._exigir_texto(
            observaciones, "Debe indicar las observaciones de la devolución.")
        WorkflowService.obtener(exp_id, tipo, session=session)
        WorkflowCumplimientoDAO.observar(exp_id, tipo, obs, usuario=usuario,
                                         fecha=_ahora(), session=session)
        return {"expediente_id": exp_id, "tipo": tipo,
                "estado_workflow": EW_SUBSANACION}

    @staticmethod
    def rechazar_cumplimiento(exp_id, tipo, motivo, usuario='', session=None):
        """Desestima el expediente en Cumplimiento y lo archiva."""
        razon = WorkflowService._exigir_texto(
            motivo, "Debe indicar el motivo del rechazo.")
        WorkflowService.obtener(exp_id, tipo, session=session)
        WorkflowCumplimientoDAO.rechazar(exp_id, tipo, razon, usuario=usuario,
                                         fecha=_ahora(), session=session)
        return {"expediente_id": exp_id, "tipo": tipo,
                "estado_workflow": EW_RECHAZADO_COMP}

    # ── Etapas posteriores ────────────────────────────────────────────
    @staticmethod
    def registrar_legal(exp_id, tipo, datos, session=None):
        """
        Firma de Legal. Exige la certificación previa de Cumplimiento.

        `datos` es el diccionario de campos que espera `update_legal` de cada
        línea de producto; el servicio no interpreta su contenido.
        """
        WorkflowService.exigir_editable(exp_id, tipo, session=session)
        WorkflowService.exigir_cumplimiento(exp_id, tipo, session=session)
        _dao(tipo).update_legal(exp_id=exp_id, session=session, **datos)
        TareaWorkflowDAO.cerrar_tareas(exp_id, tipo, etapa='Legal',
                                       estado_final='COMPLETADA', session=session)
        return {"expediente_id": exp_id, "tipo": tipo, "etapa": "Legal"}

    @staticmethod
    def registrar_riesgo(exp_id, tipo, datos, session=None):
        """Firma de Riesgo. Exige la certificación previa de Cumplimiento."""
        WorkflowService.exigir_editable(exp_id, tipo, session=session)
        WorkflowService.exigir_cumplimiento(exp_id, tipo, session=session)
        _dao(tipo).update_riesgo(exp_id=exp_id, session=session, **datos)
        TareaWorkflowDAO.cerrar_tareas(exp_id, tipo, etapa='Crédito',
                                       estado_final='COMPLETADA', session=session)
        return {"expediente_id": exp_id, "tipo": tipo, "etapa": "Crédito"}

    @staticmethod
    def emitir_dictamen(exp_id, tipo, dictamen, usuario='', tasa=0.0, plazo=None,
                        session=None):
        """
        Decisión del Comité.

        Una aprobación exige las tres firmas; un rechazo solo la certificación
        de Cumplimiento, porque puede desestimarse en cualquier punto posterior.
        """
        decision = str(dictamen or '').upper()
        if decision not in ('APROBADO', 'RECHAZADO'):
            raise DatosInsuficientes(
                "El dictamen debe ser 'APROBADO' o 'RECHAZADO'.")

        if decision == 'APROBADO':
            expediente = WorkflowService.exigir_firmas_completas(
                exp_id, tipo, session=session)
        else:
            expediente = WorkflowService.obtener(exp_id, tipo, session=session)

        dao = _dao(tipo)
        fecha = _ahora()
        if tipo == 'corp':
            dao.update_dictamen(exp_id, decision, usuario, fecha, tasa=tasa,
                                plazo=plazo if plazo is not None else 36,
                                session=session)
        else:
            dao.update_dictamen(exp_id, decision, usuario, fecha, tasa=tasa,
                                 session=session)

        if decision == 'APROBADO':
            # Importación local para mantener la dependencia del circuito en una
            # sola dirección. El mismo Session hace atómicos dictamen y cuotas.
            from services.risk_service import AmortizationService

            plazo_plan = int(
                plazo if plazo is not None
                else expediente.get('plazo_meses') or (36 if tipo == 'corp' else 48)
            )
            AmortizationService.generar(
                exp_id=exp_id,
                tipo=tipo,
                monto=float(expediente.get('monto') or 0),
                tasa_anual=float(tasa or 0),
                plazo_meses=plazo_plan,
                fecha_inicio_str=fecha,
                session=session,
            )

        TareaWorkflowDAO.cerrar_tareas(
            exp_id, tipo,
            estado_final='COMPLETADA' if decision == 'APROBADO' else 'ANULADA',
            session=session)
        return {"expediente_id": exp_id, "tipo": tipo, "dictamen": decision}

    @staticmethod
    def devolver(exp_id, tipo, etapa_destino, observaciones, usuario='', session=None):
        """Devuelve el expediente a una etapa previa con justificación obligatoria."""
        obs = WorkflowService._exigir_texto(
            observaciones, "Debe indicar la justificación de la devolución.")
        etapa = WorkflowService._exigir_texto(
            etapa_destino, "Debe indicar la etapa destino de la devolución.")
        WorkflowService.obtener(exp_id, tipo, session=session)

        _dao(tipo).devolver_expediente(exp_id=exp_id, etapa_destino=etapa,
                                       observaciones=obs, usuario=usuario,
                                       fecha=_ahora(), session=session)
        TareaWorkflowDAO.crear_tareas(exp_id, tipo, (etapa,), origen='Devolución',
                                      usuario=usuario, observaciones=obs,
                                      session=session)
        return {"expediente_id": exp_id, "tipo": tipo, "devuelto_a": etapa}

    @staticmethod
    def rechazar(exp_id, tipo, observaciones, usuario='', session=None):
        """Rechazo administrativo desde el reporte general."""
        obs = WorkflowService._exigir_texto(
            observaciones, "Debe indicar el motivo del rechazo.")
        WorkflowService.obtener(exp_id, tipo, session=session)
        _dao(tipo).rechazar_expediente(exp_id=exp_id, obs=obs, usuario=usuario,
                                       fecha=_ahora(), session=session)
        TareaWorkflowDAO.cerrar_tareas(exp_id, tipo, estado_final='ANULADA',
                                       session=session)
        return {"expediente_id": exp_id, "tipo": tipo, "dictamen": "RECHAZADO"}
