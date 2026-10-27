"use client";

import { useState } from "react";
import type {
  MetodoPagoPayload,
  PagoMixtoPayload,
  ResultadoPago,
  ResumenFinanciero,
  TasaCambio,
} from "@/hooks/useCobranzas";
import { procesarPagoMixto } from "@/hooks/useCobranzas";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { ApiError } from "@/utils/apiClient";
import { formatearDinero } from "@/utils/format";
import { IconoTarjeta, IconoDinero, IconoDocumento } from "@/components/ui/Iconos";

interface Props {
  resumen: ResumenFinanciero;
  tasaCambio: TasaCambio;
  monedaPredeterminada: "USD" | "VES" | "COP";
  montoSugeridoInicial?: number;
  alProcesarExitoso: (resultado: ResultadoPago) => void;
}

export function MatrizPagoMixto({
  resumen,
  tasaCambio,
  monedaPredeterminada,
  montoSugeridoInicial = 0,
  alProcesarExitoso,
}: Props) {
  const { notificar, notificarError } = useAvisos();
  const [enviando, setEnviando] = useState(false);
  const [destinoAbono, setDestinoAbono] = useState<"reducir_cuota" | "reducir_plazo">(
    "reducir_cuota",
  );
  const [observaciones, setObservaciones] = useState("");

  // ── Estados de Efectivo ──────────────────────────────────────────
  const [usarEfectivo, setUsarEfectivo] = useState(true);
  const [montoEfectivo, setMontoEfectivo] = useState<number>(montoSugeridoInicial || 0);
  const [monedaEfectivo, setMonedaEfectivo] = useState<"USD" | "VES">(
    monedaPredeterminada === "VES" ? "VES" : "USD",
  );
  const [recibidoEfectivo, setRecibidoEfectivo] = useState<number>(0);

  // ── Estados de Transferencia / Pago Móvil ─────────────────────────
  const [usarTransf, setUsarTransf] = useState(false);
  const [montoTransf, setMontoTransf] = useState<number>(0);
  const [monedaTransf, setMonedaTransf] = useState<"USD" | "VES">("VES");
  const [bancoOrigen, setBancoOrigen] = useState("");
  const [bancoDestino, setBancoDestino] = useState("Banesco Banco Universal");
  const [referenciaTransf, setReferenciaTransf] = useState("");

  // ── Estados de Punto de Venta / Tarjeta ────────────────────────────
  const [usarPos, setUsarPos] = useState(false);
  const [montoPos, setMontoPos] = useState<number>(0);
  const [lotePos, setLotePos] = useState("");
  const [aprobacionPos, setAprobacionPos] = useState("");
  const [tarjeta4, setTarjeta4] = useState("");

  // ── Comprobante ──────────────────────────────────────────────────
  const [comprobanteNombre, setComprobanteNombre] = useState<string>("");

  // ── Cálculos de conversión y total ────────────────────────────────
  const tasa = tasaCambio.USD_VES || 45.45;

  const aDolares = (monto: number, moneda: "USD" | "VES" | "COP") => {
    if (moneda === "USD") return monto;
    if (moneda === "VES") return monto / tasa;
    return (monto * 0.0115) / tasa;
  };

  const totalUsd =
    (usarEfectivo ? aDolares(montoEfectivo, monedaEfectivo) : 0) +
    (usarTransf ? aDolares(montoTransf, monedaTransf) : 0) +
    (usarPos ? aDolares(montoPos, "VES") : 0);

  const totalVes = totalUsd * tasa;

  // Calculadora de vuelto / cambio en efectivo
  const vueltoEfectivo =
    recibidoEfectivo > montoEfectivo && montoEfectivo > 0
      ? recibidoEfectivo - montoEfectivo
      : 0;

  const manejarEnvio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totalUsd <= 0) {
      notificar("error", "Monto inválido", "El monto total a pagar debe ser mayor a cero.");
      return;
    }

    const metodos: MetodoPagoPayload[] = [];

    if (usarEfectivo && montoEfectivo > 0) {
      metodos.push({
        tipo: "efectivo",
        monto: montoEfectivo,
        moneda: monedaEfectivo,
        monto_recibido: recibidoEfectivo || montoEfectivo,
        vuelto: vueltoEfectivo,
      });
    }

    if (usarTransf && montoTransf > 0) {
      if (!referenciaTransf.trim()) {
        notificar(
          "error",
          "Referencia requerida",
          "Debe ingresar el número de referencia bancaria para pagos por transferencia o pago móvil.",
        );
        return;
      }
      metodos.push({
        tipo: "transferencia",
        monto: montoTransf,
        moneda: monedaTransf,
        banco_origen: bancoOrigen.trim(),
        banco_destino: bancoDestino.trim(),
        referencia: referenciaTransf.trim(),
      });
    }

    if (usarPos && montoPos > 0) {
      if (!lotePos.trim() || !aprobacionPos.trim()) {
        notificar(
          "error",
          "Datos POS requeridos",
          "Debe registrar el número de lote y el código de aprobación del punto de venta.",
        );
        return;
      }
      metodos.push({
        tipo: "punto_venta",
        monto: montoPos,
        moneda: "VES",
        lote: lotePos.trim(),
        codigo_aprobacion: aprobacionPos.trim(),
        tarjeta_ultimos_4: tarjeta4.trim(),
      });
    }

    if (metodos.length === 0) {
      notificar("error", "Sin métodos", "Seleccione y complete al menos un método de pago.");
      return;
    }

    const payload: PagoMixtoPayload = {
      expediente_id: resumen.expediente_id,
      tipo_expediente: resumen.tipo,
      tasa_cambio: tasa,
      destino_abono_extra: destinoAbono,
      metodos,
      comprobante_url: comprobanteNombre,
      observaciones: observaciones.trim(),
    };

    setEnviando(true);
    try {
      const res = await procesarPagoMixto(payload);
      notificar("exito", "Pago Procesado con Éxito", `Se emitió el recibo ${res.numero_recibo}.`);
      alProcesarExitoso(res);
    } catch (err: unknown) {
      notificarError(
        err instanceof ApiError ? err : new ApiError(0, "Error al procesar el pago."),
      );
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form
      onSubmit={manejarEnvio}
      className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-borde pb-4">
        <div>
          <h3 className="text-sm font-bold text-kaizen-900 flex items-center gap-2">
            <IconoTarjeta className="h-4 w-4 text-kaizen-800" />
            <span>Procesamiento de Pago · Caja Mixta</span>
          </h3>
          <p className="mt-0.5 text-xs text-tinta-suave">
            Combine efectivo, transferencias y puntos de venta en una sola operación. Aplicación bajo Cascada Legal automática.
          </p>
        </div>

        {/* Resumen de Total a Pagar en Caja */}
        <div className="rounded-lg bg-kaizen-900 text-white px-4 py-2 text-right">
          <p className="text-[10px] text-white/70 uppercase font-semibold">Total a Imputar</p>
          <p className="text-lg font-extrabold tabular-nums">
            {formatearDinero(totalUsd)}
          </p>
          <p className="text-[10px] text-white/80 tabular-nums">
            ≈ Bs. {totalVes.toLocaleString("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* ── 1. Matriz de Métodos de Pago ──────────────────────────────── */}
      <div className="space-y-4">
        {/* Método 1: Efectivo */}
        <div className="rounded-lg border border-borde p-3.5 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={usarEfectivo}
                onChange={(e) => setUsarEfectivo(e.target.checked)}
                className="h-4 w-4 rounded border-borde text-kaizen-800 focus:ring-kaizen-600"
              />
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-kaizen-900">
                <IconoDinero className="h-4 w-4 text-slate-600" />
                <span>Efectivo en Ventanilla</span>
              </span>
            </label>
            {usarEfectivo && (
              <span className="text-[11px] font-semibold text-kaizen-700">
                Subtotal: {formatearDinero(aDolares(montoEfectivo, monedaEfectivo))}
              </span>
            )}
          </div>

          {usarEfectivo && (
            <div className="mt-3 grid gap-3 sm:grid-cols-3 pt-2 border-t border-borde/60 text-xs">
              <div>
                <label className="block text-tinta-suave mb-1">Monto a pagar</label>
                <div className="flex gap-1.5">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={montoEfectivo || ""}
                    onChange={(e) => setMontoEfectivo(Number(e.target.value))}
                    placeholder="0.00"
                    className="w-full rounded border border-borde px-2.5 py-1.5 font-bold tabular-nums outline-none focus:border-kaizen-600"
                  />
                  <select
                    value={monedaEfectivo}
                    onChange={(e) => setMonedaEfectivo(e.target.value as "USD" | "VES")}
                    className="rounded border border-borde bg-white px-2 py-1 font-semibold text-kaizen-900"
                  >
                    <option value="USD">USD</option>
                    <option value="VES">VES</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">
                  Billetes Recibidos (Calculadora)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={recibidoEfectivo || ""}
                  onChange={(e) => setRecibidoEfectivo(Number(e.target.value))}
                  placeholder="Ej. billete de 100"
                  className="w-full rounded border border-borde px-2.5 py-1.5 tabular-nums outline-none focus:border-kaizen-600"
                />
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">
                  Cambio / Vuelto a Entregar
                </label>
                <div className="rounded border border-verde-trazo/30 bg-verde-fondo/70 px-2.5 py-1.5 font-extrabold text-verde-trazo tabular-nums">
                  {vueltoEfectivo > 0
                    ? `${vueltoEfectivo.toFixed(2)} ${monedaEfectivo}`
                    : "0.00"}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Método 2: Transferencia / Pago Móvil */}
        <div className="rounded-lg border border-borde p-3.5 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={usarTransf}
                onChange={(e) => setUsarTransf(e.target.checked)}
                className="h-4 w-4 rounded border-borde text-kaizen-800 focus:ring-kaizen-600"
              />
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-kaizen-900">
                <IconoDocumento className="h-4 w-4 text-slate-600" />
                <span>Transferencia Bancaria / Pago Móvil</span>
              </span>
            </label>
            {usarTransf && (
              <span className="text-[11px] font-semibold text-kaizen-700">
                Subtotal: {formatearDinero(aDolares(montoTransf, monedaTransf))}
              </span>
            )}
          </div>

          {usarTransf && (
            <div className="mt-3 grid gap-3 sm:grid-cols-4 pt-2 border-t border-borde/60 text-xs">
              <div>
                <label className="block text-tinta-suave mb-1">Monto transferido</label>
                <div className="flex gap-1.5">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={montoTransf || ""}
                    onChange={(e) => setMontoTransf(Number(e.target.value))}
                    placeholder="0.00"
                    className="w-full rounded border border-borde px-2.5 py-1.5 font-bold tabular-nums outline-none focus:border-kaizen-600"
                  />
                  <select
                    value={monedaTransf}
                    onChange={(e) => setMonedaTransf(e.target.value as "USD" | "VES")}
                    className="rounded border border-borde bg-white px-2 py-1 font-semibold text-kaizen-900"
                  >
                    <option value="VES">VES</option>
                    <option value="USD">USD</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">
                  N° Referencia Única <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={referenciaTransf}
                  onChange={(e) => setReferenciaTransf(e.target.value)}
                  placeholder="Ej. 12345678"
                  className="w-full rounded border border-borde px-2.5 py-1.5 font-bold uppercase outline-none focus:border-kaizen-600"
                />
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">Banco Origen</label>
                <input
                  type="text"
                  value={bancoOrigen}
                  onChange={(e) => setBancoOrigen(e.target.value)}
                  placeholder="Banco emisor"
                  className="w-full rounded border border-borde px-2.5 py-1.5 outline-none focus:border-kaizen-600"
                />
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">Banco Receptor KFG</label>
                <select
                  value={bancoDestino}
                  onChange={(e) => setBancoDestino(e.target.value)}
                  className="w-full rounded border border-borde bg-white px-2.5 py-1.5 text-kaizen-900 outline-none"
                >
                  <option value="Banesco">Banesco Banco Universal</option>
                  <option value="Mercantil">Banco Mercantil</option>
                  <option value="BBVA">BBVA Provincial</option>
                  <option value="BNC">Banco Nacional de Crédito</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Método 3: Punto de Venta / Tarjeta */}
        <div className="rounded-lg border border-borde p-3.5 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={usarPos}
                onChange={(e) => setUsarPos(e.target.checked)}
                className="h-4 w-4 rounded border-borde text-kaizen-800 focus:ring-kaizen-600"
              />
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-kaizen-900">
                <IconoTarjeta className="h-4 w-4 text-slate-600" />
                <span>Punto de Venta (Tarjeta Débito/Crédito)</span>
              </span>
            </label>
            {usarPos && (
              <span className="text-[11px] font-semibold text-kaizen-700">
                Subtotal: {formatearDinero(aDolares(montoPos, "VES"))}
              </span>
            )}
          </div>

          {usarPos && (
            <div className="mt-3 grid gap-3 sm:grid-cols-4 pt-2 border-t border-borde/60 text-xs">
              <div>
                <label className="block text-tinta-suave mb-1">Monto en POS (VES)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={montoPos || ""}
                  onChange={(e) => setMontoPos(Number(e.target.value))}
                  placeholder="0.00 Bs."
                  className="w-full rounded border border-borde px-2.5 py-1.5 font-bold tabular-nums outline-none focus:border-kaizen-600"
                />
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">
                  N° de Lote <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={lotePos}
                  onChange={(e) => setLotePos(e.target.value)}
                  placeholder="Ej. 0042"
                  className="w-full rounded border border-borde px-2.5 py-1.5 font-mono outline-none focus:border-kaizen-600"
                />
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">
                  Código Aprobación <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={aprobacionPos}
                  onChange={(e) => setAprobacionPos(e.target.value)}
                  placeholder="Ej. AP8891"
                  className="w-full rounded border border-borde px-2.5 py-1.5 font-mono outline-none focus:border-kaizen-600"
                />
              </div>

              <div>
                <label className="block text-tinta-suave mb-1">Últimos 4 Dígitos</label>
                <input
                  type="text"
                  maxLength={4}
                  value={tarjeta4}
                  onChange={(e) => setTarjeta4(e.target.value)}
                  placeholder="Ej. 5432"
                  className="w-full rounded border border-borde px-2.5 py-1.5 font-mono outline-none focus:border-kaizen-600"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── 2. Mapeo de Abonos Extraordinarios y Comprobante ──────────── */}
      <div className="grid gap-4 sm:grid-cols-2 pt-2 border-t border-borde text-xs">
        <div>
          <label className="block font-semibold text-kaizen-900 mb-1">
            Destino de Abonos Excedentes a Capital:
          </label>
          <select
            value={destinoAbono}
            onChange={(e) =>
              setDestinoAbono(e.target.value as "reducir_cuota" | "reducir_plazo")
            }
            className="w-full rounded-lg border border-borde bg-white px-3 py-2 text-kaizen-900 outline-none focus:border-kaizen-600"
          >
            <option value="reducir_cuota">
              Reducir el valor de las cuotas siguientes (manteniendo el plazo)
            </option>
            <option value="reducir_plazo">
              Reducir el plazo / tiempo del crédito (eliminando cuotas finales)
            </option>
          </select>
          <p className="mt-1 text-[11px] text-tinta-suave">
            Si el pago supera los compromisos vencidos e inmediatos, la diferencia amortizará capital según la regla seleccionada.
          </p>
        </div>

        <div>
          <label className="block font-semibold text-kaizen-900 mb-1">
            Adjuntar Comprobante o Captura (Opcional):
          </label>
          <div className="flex items-center gap-2">
            <input
              type="file"
              accept="image/*,.pdf"
              id="file-comprobante"
              onChange={(e) => {
                const archivo = e.target.files?.[0];
                if (archivo) setComprobanteNombre(archivo.name);
              }}
              className="hidden"
            />
            <label
              htmlFor="file-comprobante"
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-borde bg-slate-50 px-3 py-2 text-xs font-semibold text-kaizen-800 hover:bg-slate-100"
            >
              <IconoDocumento className="h-3.5 w-3.5 text-tinta-suave" />
              <span>{comprobanteNombre || "Seleccionar captura o recibo"}</span>
            </label>
            {comprobanteNombre && (
              <button
                type="button"
                onClick={() => setComprobanteNombre("")}
                className="text-xs text-red-600 hover:underline"
              >
                Quitar
              </button>
            )}
          </div>
          <p className="mt-1 text-[11px] text-tinta-suave">
            Ideal para pagos procesados remotamente o transferencias interbancarias.
          </p>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-kaizen-900 mb-1">
          Observaciones del Pago:
        </label>
        <input
          type="text"
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
          placeholder="Notas adicionales o concepto del cobro..."
          className="w-full rounded-lg border border-borde px-3 py-2 text-xs outline-none focus:border-kaizen-600"
        />
      </div>

      {/* ── 3. Botón de Procesamiento ─────────────────────────────────── */}
      <div className="flex items-center justify-between border-t border-borde pt-4">
        <div className="text-xs text-tinta-suave">
          <span>Cascada de Aplicación: </span>
          <span className="font-semibold text-kaizen-900">
            1. Gastos → 2. Mora → 3. Interés → 4. Capital
          </span>
        </div>

        <button
          type="submit"
          disabled={enviando || totalUsd <= 0}
          className="inline-flex items-center gap-2 rounded-lg bg-verde-trazo px-6 py-2.5 text-sm font-bold text-white shadow-sm hover:brightness-90 transition disabled:opacity-50"
        >
          {enviando && <Girador />}
          {enviando
            ? "Procesando Cobro…"
            : `Procesar Pago por ${formatearDinero(totalUsd)}`}
        </button>
      </div>
    </form>
  );
}
