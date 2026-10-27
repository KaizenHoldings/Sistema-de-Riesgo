"use client";

import Link from "next/link";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { useExpedientesAutomotrices, useExpedientesCorporativos } from "@/hooks/useExpedientes";
import type { ExpedienteBase, TipoExpediente } from "@/types/api";
import { formatearFecha, textoOGuion } from "@/utils/format";

interface Evento extends ExpedienteBase { tipo: TipoExpediente }

export function HistorialExpedientes({ cliente }: { cliente: string }) {
  const filtros = { pagina: 1, porPagina: 200, cliente };
  const corporativos = useExpedientesCorporativos(filtros);
  const automotrices = useExpedientesAutomotrices(filtros);
  const error = corporativos.error ?? automotrices.error;
  if (error) return <Alerta error={error} alReintentar={() => { corporativos.recargar(); automotrices.recargar(); }} />;

  const eventos: Evento[] = [
    ...(corporativos.datos ?? []).map((e) => ({ ...e, tipo: "corp" as const })),
    ...(automotrices.datos ?? []).map((e) => ({ ...e, tipo: "auto" as const })),
  ].sort((a, b) => String(b.fecha ?? "").localeCompare(String(a.fecha ?? "")));
  if (!eventos.length) return <SinResultados mensaje="Este cliente todavía no tiene solicitudes asociadas." />;

  return <section className="rounded-xl border border-borde bg-white p-6 shadow-sm">
    <h2 className="mb-5 font-bold text-kaizen-900">Historial de solicitudes</h2>
    <ol className="relative ml-3 border-l-2 border-kaizen-100">
      {eventos.map((evento) => <li key={`${evento.tipo}-${evento.id}`} className="mb-6 ml-6 last:mb-0">
        <span className="absolute -left-2 mt-1 h-3.5 w-3.5 rounded-full bg-[#1E3A8A] ring-4 ring-white" />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><p className="font-semibold text-[#0B1D4E]">{evento.tipo === "corp" ? "Crédito corporativo" : "Crédito automotriz"} #{evento.id}</p><p className="text-sm text-tinta-suave">{formatearFecha(evento.fecha)} · {textoOGuion(evento.descripcion)}</p></div>
          <div className="text-right"><p className="text-sm font-semibold text-[#0B1D4E]">{textoOGuion(evento.dictamen)}</p><Link className="text-sm font-semibold text-[#1E3A8A] hover:underline" href={`/evaluations/${evento.tipo}/${evento.id}`}>Ver expediente</Link></div>
        </div>
      </li>)}
    </ol>
  </section>;
}
