"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta } from "@/components/ui/Alerta";
import { type NuevoCliente, useCrearCliente } from "@/hooks/useClientes";

const campo = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-[#0B1D4E] outline-none focus:border-[#1E3A8A] focus:ring-2 focus:ring-blue-100";
const hoy = new Date().toISOString().slice(0, 10);

export default function RegistrarClientePage() {
  const router = useRouter();
  const [form, setForm] = useState<NuevoCliente>({
    fecha_registro: hoy, tipo: "Natural", nombre: "", cedula_rif: "",
    fecha_nacimiento: "", nacionalidad: "Venezolana", telefono: "", email: "",
    direccion: "", actividad_economica: "", nombre_rep: "", cedula_rep: "",
    cargo_rep: "", docs_json: "{}",
  });
  const accion = useCrearCliente();
  const cambiar = (clave: keyof NuevoCliente, valor: string) =>
    setForm((actual) => ({ ...actual, [clave]: valor }));
  const guardar = async (evento: FormEvent) => {
    evento.preventDefault();
    const creado = await accion.ejecutar(form);
    if (creado?.id) router.push(`/clients/${creado.id}`);
  };

  return <>
    <EncabezadoPagina icono="+" miga="Clientes / Alta" titulo="Registrar cliente" bajada="Incorpore una persona natural o jurídica al padrón KYC." />
    <form onSubmit={guardar} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="grid gap-5 md:grid-cols-2">
        <Campo etiqueta="Tipo"><select className={campo} value={form.tipo ?? "Natural"} onChange={(e) => cambiar("tipo", e.target.value)}><option>Natural</option><option>Jurídica</option></select></Campo>
        <Campo etiqueta="Nombre o razón social"><input required className={campo} value={form.nombre ?? ""} onChange={(e) => cambiar("nombre", e.target.value)} /></Campo>
        <Campo etiqueta="Cédula o RIF"><input required className={campo} value={form.cedula_rif ?? ""} onChange={(e) => cambiar("cedula_rif", e.target.value)} /></Campo>
        <Campo etiqueta="Fecha de nacimiento/constitución"><input type="date" className={campo} value={form.fecha_nacimiento ?? ""} onChange={(e) => cambiar("fecha_nacimiento", e.target.value)} /></Campo>
        <Campo etiqueta="Nacionalidad"><input className={campo} value={form.nacionalidad ?? ""} onChange={(e) => cambiar("nacionalidad", e.target.value)} /></Campo>
        <Campo etiqueta="Teléfono"><input className={campo} value={form.telefono ?? ""} onChange={(e) => cambiar("telefono", e.target.value)} /></Campo>
        <Campo etiqueta="Correo"><input type="email" className={campo} value={form.email ?? ""} onChange={(e) => cambiar("email", e.target.value)} /></Campo>
        <Campo etiqueta="Actividad económica"><input className={campo} value={form.actividad_economica ?? ""} onChange={(e) => cambiar("actividad_economica", e.target.value)} /></Campo>
        <Campo etiqueta="Dirección" ancho><textarea rows={3} className={campo} value={form.direccion ?? ""} onChange={(e) => cambiar("direccion", e.target.value)} /></Campo>
        {form.tipo !== "Natural" && <>
          <Campo etiqueta="Representante legal"><input className={campo} value={form.nombre_rep ?? ""} onChange={(e) => cambiar("nombre_rep", e.target.value)} /></Campo>
          <Campo etiqueta="Cédula del representante"><input className={campo} value={form.cedula_rep ?? ""} onChange={(e) => cambiar("cedula_rep", e.target.value)} /></Campo>
          <Campo etiqueta="Cargo"><input className={campo} value={form.cargo_rep ?? ""} onChange={(e) => cambiar("cargo_rep", e.target.value)} /></Campo>
        </>}
      </div>
      {accion.error && <div className="mt-5"><Alerta error={accion.error} /></div>}
      <button disabled={accion.enviando} className="mt-6 rounded-lg bg-[#1E3A8A] px-5 py-2.5 font-semibold text-white hover:bg-[#0B1D4E] disabled:opacity-50">{accion.enviando ? "Guardando…" : "Registrar cliente"}</button>
    </form>
  </>;
}

function Campo({ etiqueta, ancho, children }: { etiqueta: string; ancho?: boolean; children: React.ReactNode }) {
  return <label className={ancho ? "md:col-span-2" : ""}><span className="text-sm font-semibold text-[#0B1D4E]">{etiqueta}</span>{children}</label>;
}
