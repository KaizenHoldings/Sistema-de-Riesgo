"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient, ApiError, type Descarga } from "@/utils/apiClient";
import type { TipoExpediente } from "@/types/api";

export interface TasaCambio {
  USD_VES: number;
  EUR_VES: number;
  COP_VES: number;
  fecha: string;
  fuente: string;
  fijada: boolean;
}

export interface CreditoEncontrado {
  id: number;
  tipo: TipoExpediente;
  codigo_credito: string;
  cliente: string;
  documento: string;
  monto: number;
  dictamen: string;
  estado_cobranza: string;
  fecha: string;
  tasa_aprobada: number;
  plazo_meses: number;
  saldo_capital: number;
  cuotas_pendientes: number;
}

export interface ResumenFinanciero {
  expediente_id: number;
  tipo: TipoExpediente;
  codigo_credito: string;
  cliente: string;
  documento: string;
  monto_original: number;
  tasa_aprobada: number;
  plazo_meses: number;
  saldo_capital: number;
  saldo_total_deuda: number;
  total_pagado_cliente?: number;
  capital_amortizado?: number;
  intereses_pagados?: number;
  dias_atraso: number;
  num_cuotas_vencidas: number;
  monto_cuotas_vencidas: number;
  intereses_mora: number;
  gastos_cobranza: number;
  monto_ponerse_al_dia: number;
  proyeccion_cancelacion_total: number;
  ahorro_intereses_no_causados: number;
  fecha_proxima_cuota: string;
  monto_proxima_cuota: number;
  cuotas_totales: number;
  cuotas_pagadas: number;
  plan_pagos: Array<{
    id: number;
    periodo: number;
    fecha_pago: string;
    cuota: number;
    capital: number;
    interes: number;
    saldo: number;
    estado: string;
  }>;
}

export interface MetodoPagoPayload {
  tipo: "efectivo" | "transferencia" | "pago_movil" | "punto_venta";
  monto: number;
  moneda: "USD" | "VES" | "COP";
  monto_recibido?: number;
  vuelto?: number;
  banco_origen?: string;
  banco_destino?: string;
  referencia?: string;
  lote?: string;
  codigo_aprobacion?: string;
  tarjeta_ultimos_4?: string;
}

export interface PagoMixtoPayload {
  expediente_id: number;
  tipo_expediente: TipoExpediente;
  tasa_cambio: number;
  destino_abono_extra: "reducir_cuota" | "reducir_plazo";
  metodos: MetodoPagoPayload[];
  comprobante_url?: string;
  observaciones?: string;
}

export interface ResultadoPago {
  pago_id: number;
  numero_recibo: string;
  expediente_id: number;
  tipo_expediente: TipoExpediente;
  cliente: string;
  monto_total_usd: number;
  monto_total_ves: number;
  tasa_cambio: number;
  fecha: string;
  cajero: string;
  cascada: {
    gastos_cobranza: number;
    intereses_mora: number;
    interes_corriente: number;
    abono_capital: number;
    cuotas_liquidadas: number[];
    saldo_anterior: number;
    nuevo_saldo: number;
  };
  metodos: MetodoPagoPayload[];
}

export interface ArqueoResumen {
  fecha: string;
  total_usd: number;
  total_ves: number;
  efectivo_usd: number;
  efectivo_ves: number;
  pos_ves: number;
  transferencias_ves: number;
  total_transacciones: number;
  transacciones: Array<{
    id: number;
    recibo: string;
    expediente: string;
    monto_usd: number;
    monto_ves: number;
    referencia: string;
    cajero: string;
  }>;
}

export function useTasaCambio() {
  const [tasa, setTasa] = useState<TasaCambio>({
    USD_VES: 45.45,
    EUR_VES: 49.10,
    COP_VES: 0.0115,
    fecha: new Date().toISOString().slice(0, 10),
    fuente: "Banco Central de Venezuela (BCV)",
    fijada: true,
  });
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    apiClient.get<TasaCambio>("/api/v1/cobranza/tasas-cambio")
      .then((res: TasaCambio) => {
        if (!cancelado) {
          setTasa(res);
          setCargando(false);
        }
      })
      .catch(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  return { tasa, cargando };
}

export async function buscarCreditos(q: string = ""): Promise<CreditoEncontrado[]> {
  const queryParam = q.trim() ? `?q=${encodeURIComponent(q.trim())}` : "";
  return apiClient.get<CreditoEncontrado[]>(
    `/api/v1/cobranza/creditos/buscar${queryParam}`,
  );
}

export function useCreditosCartera(termino: string = "") {
  const [creditos, setCreditos] = useState<CreditoEncontrado[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => {
    setCargando(true);
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    let cancelado = false;
    buscarCreditos(termino)
      .then((data) => {
        if (!cancelado) {
          setCreditos(data);
          setCargando(false);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelado) {
          const mensaje = err instanceof ApiError ? err.message : "Error al obtener créditos de cartera";
          setError(mensaje);
          setCargando(false);
        }
      });

    return () => {
      cancelado = true;
    };
  }, [termino, version]);

  return { creditos, cargando, error, recargar };
}

export function useResumenFinanciero(tipo: TipoExpediente | null, expId: number | null) {
  const [resumen, setResumen] = useState<ResumenFinanciero | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    if (!tipo || !expId) return;

    let cancelado = false;
    apiClient.get<ResumenFinanciero>(`/api/v1/cobranza/creditos/${tipo}/${expId}/resumen-financiero`)
      .then((data: ResumenFinanciero) => {
        if (!cancelado) {
          setResumen(data);
          setCargando(false);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelado) {
          const mensaje = err instanceof ApiError ? err.message : "Error al cargar datos financieros";
          setError(mensaje);
          setCargando(false);
        }
      });

    return () => {
      cancelado = true;
    };
  }, [tipo, expId, version]);

  return {
    resumen: tipo && expId ? resumen : null,
    cargando,
    error,
    recargar,
  };
}

export async function procesarPagoMixto(payload: PagoMixtoPayload): Promise<ResultadoPago> {
  return apiClient.post<ResultadoPago>("/api/v1/cobranza/pagos/mixto", payload);
}

export async function descargarReciboPdf(pagoId: number): Promise<Descarga> {
  return apiClient.descargar(`/api/v1/cobranza/recibos/${pagoId}/pdf`);
}

export function useHistorialPagos(tipo: TipoExpediente | null, expId: number | null) {
  const [pagos, setPagos] = useState<Array<Record<string, unknown>>>([]);
  const [cargando, setCargando] = useState(false);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    if (!tipo || !expId) return;

    let cancelado = false;
    apiClient.get<Array<Record<string, unknown>>>(`/api/v1/cobranza/expedientes/${tipo}/${expId}/pagos`)
      .then((data: Array<Record<string, unknown>>) => {
        if (!cancelado) {
          setPagos(data);
          setCargando(false);
        }
      })
      .catch(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [tipo, expId, version]);

  return {
    pagos: tipo && expId ? pagos : [],
    cargando,
    recargar,
  };
}

export function useArqueoDiario(fecha?: string) {
  const [arqueo, setArqueo] = useState<ArqueoResumen | null>(null);
  const [cargando, setCargando] = useState(false);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelado = false;
    const query = fecha ? `?fecha=${fecha}` : "";
    apiClient.get<ArqueoResumen>(`/api/v1/cobranza/arqueo/hoy${query}`)
      .then((data: ArqueoResumen) => {
        if (!cancelado) {
          setArqueo(data);
          setCargando(false);
        }
      })
      .catch(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [fecha, version]);

  return { arqueo, cargando, recargar };
}

export async function cerrarArqueo(datos: {
  fecha?: string;
  efectivo_declarado_usd: number;
  efectivo_declarado_ves: number;
  pos_declarado_ves: number;
  transferencias_declarado_ves: number;
  observaciones?: string;
}): Promise<Record<string, unknown>> {
  return apiClient.post<Record<string, unknown>>("/api/v1/cobranza/arqueo/cierre", datos);
}

export interface CobroReciente {
  id: number;
  numero_recibo: string;
  hora: string;
  fecha: string;
  cliente: string;
  tipo_expediente: TipoExpediente;
  expediente_id: number;
  monto_usd: number;
  monto_ves: number;
  metodo: string;
  referencia: string;
  cajero: string;
}

export interface AlertaVencimiento {
  id: number;
  expediente_id: number;
  tipo_expediente: TipoExpediente;
  codigo_credito: string;
  periodo: number;
  cliente: string;
  documento: string;
  telefono: string;
  cuota: number;
  fecha_pago: string;
  dias_atraso: number;
  dias_texto: string;
  estado_alerta: "vencido" | "hoy" | "por_vencer";
}

export function useUltimosCobros(limite: number = 15) {
  const [cobros, setCobros] = useState<CobroReciente[]>([]);
  const [cargando, setCargando] = useState(true);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelado = false;
    apiClient.get<CobroReciente[]>(`/api/v1/cobranza/ultimos-cobros?limite=${limite}`)
      .then((data: CobroReciente[]) => {
        if (!cancelado) {
          setCobros(data);
          setCargando(false);
        }
      })
      .catch(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [limite, version]);

  return { cobros, cargando, recargar };
}

export function useAlertasCobro(dias: number = 30) {
  const [alertas, setAlertas] = useState<AlertaVencimiento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelado = false;
    apiClient.get<AlertaVencimiento[]>(`/api/v1/cobranza/alertas-vencimientos?dias=${dias}`)
      .then((data: AlertaVencimiento[]) => {
        if (!cancelado) {
          setAlertas(data);
          setCargando(false);
        }
      })
      .catch(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [dias, version]);

  return { alertas, cargando, recargar };
}

export async function descargarFiniquitoPdf(expId: number, tipo: string): Promise<Descarga> {
  return apiClient.descargar(`/api/v1/cobranza/creditos/${tipo}/${expId}/finiquito/pdf`);
}

export interface CreditoPagado {
  id: number;
  tipo: TipoExpediente;
  codigo_credito: string;
  cliente: string;
  documento: string;
  monto_original: number;
  tasa_aprobada: number;
  plazo_meses: number;
  cuotas_totales: number;
  cuotas_pagadas: number;
  total_capital_pagado: number;
  total_intereses_pagados: number;
  total_pagado: number;
  saldo_capital: number;
  estado_cobranza: string;
  fecha_aprobacion: string;
  fecha_liquidacion: string;
  recibos_emitidos: number;
  cajero_ultimo_cobro: string;
}

export interface ResumenCreditosPagados {
  total_creditos_pagados: number;
  monto_total_prestado: number;
  monto_total_recaudado: number;
  total_intereses_cobrados: number;
  tasa_cumplimiento: number;
}

export interface RespuestaCreditosPagados {
  resumen: ResumenCreditosPagados;
  creditos: CreditoPagado[];
}

export function useCreditosPagados() {
  const [datos, setDatos] = useState<RespuestaCreditosPagados>({
    resumen: {
      total_creditos_pagados: 0,
      monto_total_prestado: 0,
      monto_total_recaudado: 0,
      total_intereses_cobrados: 0,
      tasa_cumplimiento: 0,
    },
    creditos: [],
  });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(() => {
    setCargando(true);
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    let cancelado = false;
    apiClient
      .get<RespuestaCreditosPagados>("/api/v1/cobranza/creditos/pagados")
      .then((res) => {
        if (!cancelado) {
          setDatos(res);
          setCargando(false);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelado) {
          const mensaje =
            err instanceof ApiError ? err.message : "Error al obtener créditos pagados";
          setError(mensaje);
          setCargando(false);
        }
      });

    return () => {
      cancelado = true;
    };
  }, [version]);

  return {
    resumen: datos.resumen,
    creditos: datos.creditos,
    cargando,
    error,
    recargar,
  };
}

