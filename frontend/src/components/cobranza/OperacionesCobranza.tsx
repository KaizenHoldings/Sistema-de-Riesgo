"use client";

import { FormEvent, useState, useMemo } from "react";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { useAvisos } from "@/components/ui/Toast";
import { registrarGestion, registrarPago, useGestiones } from "@/hooks/useCartera";
import type { TipoExpediente } from "@/types/api";
import { formatearFecha, textoOGuion } from "@/utils/format";
import { ApiError } from "@/utils/apiClient";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";

const campo = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-[#0B1D4E] outline-none focus:border-[#1E3A8A]";
const hoy = new Date().toISOString().slice(0, 10);

export function OperacionesCobranza({ responsable }: { responsable: string }) {
  const gestiones = useGestiones();
  const { notificar } = useAvisos();
  const [expedienteId, setExpedienteId] = useState(0);
  const [tipo, setTipo] = useState<TipoExpediente>("corp");
  const [monto, setMonto] = useState(0);
  const [referencia, setReferencia] = useState("");
  const [tipoGestion, setTipoGestion] = useState("Llamada");
  const [resultado, setResultado] = useState("");
  const [proximaAccion, setProximaAccion] = useState("");
  const [fechaProxima, setFechaProxima] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [busqueda, setBusqueda] = useState("");

  const pago = async (e: FormEvent) => {
    e.preventDefault(); setEnviando(true); setError(null);
    try {
      await registrarPago({ expediente_id: expedienteId, tipo_expediente: tipo, fecha_pago: hoy, monto, referencia });
      notificar("exito", "Pago registrado", "El ingreso quedó aplicado al expediente.");
      setMonto(0); setReferencia("");
    } catch (fallo) { setError(fallo as ApiError); } finally { setEnviando(false); }
  };
  const gestion = async (e: FormEvent) => {
    e.preventDefault(); setEnviando(true); setError(null);
    try {
      await registrarGestion({ expediente_id: expedienteId, tipo_expediente: tipo, fecha: hoy, tipo_gestion: tipoGestion, responsable, resultado, proxima_accion: proximaAccion, fecha_proxima: fechaProxima, obs: "" });
      notificar("exito", "Gestión registrada", "La actividad quedó incorporada a la bitácora.");
      setResultado(""); setProximaAccion(""); gestiones.recargar();
    } catch (fallo) { setError(fallo as ApiError); } finally { setEnviando(false); }
  };

  return <div className="space-y-6">
    <div className="grid gap-6 xl:grid-cols-2">
      <Formulario titulo="Registrar pago" onSubmit={pago}>
        <Base tipo={tipo} expedienteId={expedienteId} setTipo={setTipo} setExpedienteId={setExpedienteId} />
        <Campo etiqueta="Monto"><input required min="0.01" step="0.01" type="number" className={campo} value={monto || ""} onChange={(e) => setMonto(Number(e.target.value))} /></Campo>
        <Campo etiqueta="Referencia bancaria"><input required className={campo} value={referencia} onChange={(e) => setReferencia(e.target.value)} /></Campo>
        <Boton enviando={enviando}>Aplicar pago</Boton>
      </Formulario>
      <Formulario titulo="Registrar gestión" onSubmit={gestion}>
        <Base tipo={tipo} expedienteId={expedienteId} setTipo={setTipo} setExpedienteId={setExpedienteId} />
        <Campo etiqueta="Canal"><select className={campo} value={tipoGestion} onChange={(e) => setTipoGestion(e.target.value)}><option>Llamada</option><option>Correo</option><option>Visita</option><option>WhatsApp</option></select></Campo>
        <Campo etiqueta="Resultado"><input required className={campo} value={resultado} onChange={(e) => setResultado(e.target.value)} /></Campo>
        <Campo etiqueta="Próxima acción"><input className={campo} value={proximaAccion} onChange={(e) => setProximaAccion(e.target.value)} /></Campo>
        <Campo etiqueta="Fecha próxima"><input type="date" className={campo} value={fechaProxima} onChange={(e) => setFechaProxima(e.target.value)} /></Campo>
        <Boton enviando={enviando}>Guardar gestión</Boton>
      </Formulario>
    </div>
    {error && <Alerta error={error} />}
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <h2 className="font-bold text-[#0B1D4E]">Bitácora reciente</h2>
        {gestiones.datos && gestiones.datos.length > 0 && (
          <div className="w-full sm:max-w-xs">
            <BuscadorTabla
              valor={busqueda}
              alCambiar={setBusqueda}
              placeholder="Buscar en la bitácora..."
            />
          </div>
        )}
      </div>

      {gestiones.error ? (
        <Alerta error={gestiones.error} alReintentar={gestiones.recargar} />
      ) : !gestiones.datos?.length ? (
        <SinResultados mensaje="No hay gestiones registradas." />
      ) : (
        (() => {
          const filtradas = gestiones.datos.filter((g) => {
            if (!busqueda.trim()) return true;
            const q = busqueda.toLowerCase().trim();
            return (
              `${g.tipo_expediente} #${g.expediente_id}`.toLowerCase().includes(q) ||
              String(g.tipo_gestion || "").toLowerCase().includes(q) ||
              String(g.responsable || "").toLowerCase().includes(q) ||
              String(g.resultado || "").toLowerCase().includes(q) ||
              String(g.proxima_accion || "").toLowerCase().includes(q)
            );
          });

          if (filtradas.length === 0) {
            return (
              <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-xs text-slate-500">
                No se encontraron gestiones que coincidan con &ldquo;{busqueda}&rdquo;.
              </div>
            );
          }

          return (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b text-[#0B1D4E]">
                  <tr>
                    <th className="p-2">Fecha</th>
                    <th>Expediente</th>
                    <th>Canal</th>
                    <th>Responsable</th>
                    <th>Resultado</th>
                    <th>Próxima acción</th>
                  </tr>
                </thead>
                <tbody>
                  {filtradas.map((g, i) => (
                    <tr key={g.id ?? i} className="border-b border-slate-100">
                      <td className="p-2">{formatearFecha(g.fecha)}</td>
                      <td>{g.tipo_expediente} #{g.expediente_id}</td>
                      <td>{textoOGuion(g.tipo_gestion)}</td>
                      <td>{textoOGuion(g.responsable)}</td>
                      <td>{textoOGuion(g.resultado)}</td>
                      <td>{textoOGuion(g.proxima_accion)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()
      )}
    </section>
  </div>;
}

function Base({ tipo, expedienteId, setTipo, setExpedienteId }: { tipo: TipoExpediente; expedienteId: number; setTipo: (v: TipoExpediente) => void; setExpedienteId: (v: number) => void }) { return <><Campo etiqueta="Producto"><select className={campo} value={tipo} onChange={(e) => setTipo(e.target.value as TipoExpediente)}><option value="corp">Corporativo</option><option value="auto">Automotriz</option></select></Campo><Campo etiqueta="Expediente"><input required min="1" type="number" className={campo} value={expedienteId || ""} onChange={(e) => setExpedienteId(Number(e.target.value))} /></Campo></>; }
function Formulario({ titulo, onSubmit, children }: { titulo: string; onSubmit: (e: FormEvent) => void; children: React.ReactNode }) { return <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold text-[#0B1D4E]">{titulo}</h2>{children}</form>; }
function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) { return <label className="block"><span className="text-sm font-semibold text-[#0B1D4E]">{etiqueta}</span>{children}</label>; }
function Boton({ enviando, children }: { enviando: boolean; children: React.ReactNode }) { return <button disabled={enviando} className="rounded-lg bg-[#1E3A8A] px-5 py-2.5 font-semibold text-white hover:bg-[#0B1D4E] disabled:opacity-50">{children}</button>; }
