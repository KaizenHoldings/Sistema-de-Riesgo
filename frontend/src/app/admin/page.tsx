"use client";

/**
 * Configuración del motor de riesgo y cuentas de acceso.
 *
 * Los pesos y el pricing gobiernan el scoring de toda la cartera, así que la
 * pantalla muestra junto a cada bloque la fórmula que alimenta: cambiar un peso
 * sin ver dónde entra es la forma más rápida de descalibrar el motor.
 *
 * Los parámetros se guardan en una sola llamada por línea de producto, porque el
 * backend los aplica en una única transacción: una política a medio guardar
 * dejaría el motor calificando con pesos incoherentes.
 */

import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta } from "@/components/ui/Alerta";
import { BOTON, CAMPO, Modal } from "@/components/ui/Modal";
import { Paginador } from "@/components/ui/Paginador";
import { Insignia } from "@/components/ui/Semaforo";
import { Girador, SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { Tabla, type Columna } from "@/components/ui/Tabla";
import { useAvisos } from "@/components/ui/Toast";
import { useAccion } from "@/hooks/useAccion";
import {
  cambiarContrasena,
  guardarParametros,
  guardarUsuario,
  useParametros,
  useUsuarios,
} from "@/hooks/useAdmin";
import type { UsuarioCuenta } from "@/types/api";
import { textoOGuion } from "@/utils/format";

/**
 * Roles que admite el alta de cuentas.
 *
 * Es la misma lista que valida `system_routes.ROLES` en el backend: un valor
 * que no este alli se rechaza con 422, asi que las dos tienen que coincidir
 * literalmente, acentos incluidos.
 */
const ROLES = [
  "Comercial",
  "Compliance",
  "Legal",
  "Riesgo",
  "Comité",
  "Cobranzas",
  "Superadmin",
] as const;

interface CampoParametro {
  clave: string;
  etiqueta: string;
  paso: number;
  ayuda?: string;
}

const CORPORATIVO: CampoParametro[] = [
  { clave: "w_liq", etiqueta: "Peso de liquidez", paso: 0.1 },
  { clave: "w_sol", etiqueta: "Peso de solvencia", paso: 0.1 },
  { clave: "w_cob", etiqueta: "Peso de cobertura", paso: 0.1 },
  {
    clave: "kc_boost_max",
    etiqueta: "Boost máximo Kaizen (%)",
    paso: 1,
    ayuda: "Mejora máxima que la matriz Kaizen puede aportar al score.",
  },
  { clave: "tasa_base", etiqueta: "Tasa base (%)", paso: 0.5 },
  {
    clave: "factor_riesgo",
    etiqueta: "Factor de riesgo",
    paso: 0.1,
    ayuda: "Puntos de tasa que suma cada punto de score por debajo de 10.",
  },
];

const AUTOMOTRIZ: CampoParametro[] = [
  { clave: "w_cap", etiqueta: "Peso de capacidad de pago", paso: 0.1 },
  { clave: "w_ltv_auto", etiqueta: "Peso del LTV del vehículo", paso: 0.1 },
  { clave: "w_est", etiqueta: "Peso de estabilidad laboral", paso: 0.1 },
  { clave: "kc_boost_max_auto", etiqueta: "Boost máximo Kaizen (%)", paso: 1 },
  { clave: "tasa_base_auto", etiqueta: "Tasa base automotriz (%)", paso: 0.5 },
  { clave: "factor_riesgo_auto", etiqueta: "Factor de riesgo automotriz", paso: 0.1 },
];

const FORMULAS = {
  corp: [
    "S_base = (Liq·W_liq + Solv·W_sol + Cob·W_cob) / (W_liq + W_sol + W_cob)",
    "S_final = min(S_base · (1 + KC/10 · Boost), 10)",
    "Tasa = Tasa_base + (10 − S_final) · Factor_riesgo",
  ],
  auto: [
    "S_base = (Cap·W_cap + LTV·W_ltv + Est·W_est) / (W_cap + W_ltv + W_est)",
    "S_final = min(S_base · (1 + KC/10 · Boost), 10)",
    "Tasa = Tasa_base_auto + (10 − S_final) · Factor_riesgo_auto",
  ],
} as const;

type Pestana = "corp" | "auto" | "usuarios";

const PESTANAS_VALIDAS: Pestana[] = ["corp", "auto", "usuarios"];

/** Filas por pagina, igual que en el resto de las tablas. */
const POR_PAGINA = 10;

/**
 * `useSearchParams` obliga a un limite de Suspense: sin el, la compilacion de
 * produccion falla al intentar prerenderizar la pagina.
 */
export default function AdminPage() {
  return (
    <Suspense fallback={<SkeletonMetricas tarjetas={3} />}>
      <PanelAdministracion />
    </Suspense>
  );
}

function PanelAdministracion() {
  // El panel de configuracion enlaza cada tarjeta con su pestana; sin el
  // parametro se abre la primera, como antes.
  const parametros = useSearchParams();
  const pedida = parametros.get("seccion");
  const [pestana, setPestana] = useState<Pestana>(
    PESTANAS_VALIDAS.includes(pedida as Pestana) ? (pedida as Pestana) : "corp",
  );

  return (
    <>
      <EncabezadoPagina
        icono="⚙"
        miga="Inicio / Administración"
        titulo="Configuración del motor de riesgo"
        bajada="Pesos de calificación, política de pricing y cuentas de acceso."
      />

      <div
        className="mb-6 inline-flex flex-wrap rounded-lg border border-borde bg-white p-1"
        role="tablist"
      >
        {(
          [
            ["corp", "Crédito corporativo"],
            ["auto", "Crédito automotriz"],
            ["usuarios", "Usuarios y roles"],
          ] as Array<[Pestana, string]>
        ).map(([valor, etiqueta]) => (
          <button
            key={valor}
            type="button"
            role="tab"
            aria-selected={pestana === valor}
            onClick={() => setPestana(valor)}
            className={`rounded-md px-4 py-2 text-sm font-semibold transition ${
              pestana === valor
                ? "bg-kaizen-800 text-white"
                : "text-tinta-suave hover:text-kaizen-900"
            }`}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      {pestana === "usuarios" ? (
        <PanelUsuarios />
      ) : (
        <PanelParametros
          campos={pestana === "corp" ? CORPORATIVO : AUTOMOTRIZ}
          formulas={FORMULAS[pestana]}
          titulo={
            pestana === "corp"
              ? "Política de crédito corporativo"
              : "Política de crédito automotriz"
          }
        />
      )}
    </>
  );
}

function PanelParametros({
  campos,
  formulas,
  titulo,
}: {
  campos: CampoParametro[];
  formulas: readonly string[];
  titulo: string;
}) {
  const { datos, cargando, error, recargar } = useParametros();
  const { notificar } = useAvisos();

  // El formulario no copia los valores de la base a un estado propio: los deriva
  // mientras nadie ha tocado nada, y solo pasa a mandar el estado local en cuanto
  // se edita un campo. Así una recarga no pisa lo escrito y, tras guardar, basta
  // con soltar la edición para volver a reflejar lo que quedó almacenado.
  const [editados, setEditados] = useState<Record<string, string> | null>(null);

  const almacenados = useMemo(() => {
    const base: Record<string, string> = {};
    for (const parametro of datos ?? []) {
      base[parametro.clave] = String(parametro.valor ?? 0);
    }
    return base;
  }, [datos]);

  const valores = editados ?? almacenados;

  const editar = (clave: string, valor: string) =>
    setEditados({ ...valores, [clave]: valor });

  const guardar = useAccion(async () => {
    const cambios = campos.map((campo) => ({
      clave: campo.clave,
      valor: Number(valores[campo.clave] ?? 0),
    }));
    return guardarParametros(cambios);
  });

  if (cargando) return <SkeletonMetricas />;
  if (error) return <Alerta error={error} alReintentar={recargar} />;

  const enviar = async () => {
    const resultado = await guardar.ejecutar();
    if (resultado) {
      notificar("exito", "Política actualizada", `Se guardó la ${titulo.toLowerCase()}.`);
      setEditados(null);
      recargar();
    }
  };

  return (
    <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="rounded-xl border border-borde bg-white p-5 shadow-sm lg:col-span-2">
        <h2 className="text-sm font-semibold text-kaizen-900">{titulo}</h2>
        <p className="mt-1 text-sm text-tinta-suave">
          Los cambios se aplican de inmediato a las evaluaciones que aún no tienen
          score registrado.
        </p>

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {campos.map((campo) => (
            <label key={campo.clave} className="block">
              <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
                {campo.etiqueta}
              </span>
              <input
                type="number"
                step={campo.paso}
                min="0"
                value={valores[campo.clave] ?? ""}
                onChange={(evento) => editar(campo.clave, evento.target.value)}
                className={`mt-1.5 ${CAMPO}`}
              />
              <span className="mt-1 block font-mono text-xs text-tinta-suave">
                {campo.clave}
              </span>
              {campo.ayuda && (
                <span className="mt-1 block text-xs text-tinta-suave">
                  {campo.ayuda}
                </span>
              )}
            </label>
          ))}
        </div>

        {guardar.error && (
          <div className="mt-5">
            <Alerta error={guardar.error} />
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            className={BOTON.primario}
            disabled={guardar.enviando}
            onClick={enviar}
          >
            {guardar.enviando && <Girador />}
            Guardar política
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-borde bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-kaizen-900">
          Dónde entran estos valores
        </h2>
        <ul className="mt-4 space-y-3">
          {formulas.map((formula) => (
            <li
              key={formula}
              className="scroll-fino overflow-x-auto rounded-lg bg-kaizen-100/40 px-4 py-3 font-mono text-xs whitespace-nowrap text-kaizen-900"
            >
              {formula}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-tinta-suave">
          El cálculo lo resuelve el backend; esta pantalla solo edita los valores
          que alimentan esas fórmulas.
        </p>
      </div>
    </section>
  );
}

function PanelUsuarios() {
  const { datos, cargando, error, recargar } = useUsuarios();
  const { notificar } = useAvisos();
  const [alta, setAlta] = useState(false);
  const [cuenta, setCuenta] = useState<UsuarioCuenta | null>(null);
  const [pagina, setPagina] = useState(1);

  const columnas: Array<Columna<UsuarioCuenta>> = [
    {
      clave: "accion",
      encabezado: "",
      celda: (u) => (
        <button
          type="button"
          onClick={() => setCuenta(u)}
          className="rounded-lg border border-borde px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition hover:border-kaizen-600 hover:text-kaizen-600"
        >
          Cambiar contraseña
        </button>
      ),
    },
    {
      clave: "usuario",
      encabezado: "Cuenta",
      anchoMinimo: "18rem",
      celda: (u) => (
        <span className="font-semibold text-kaizen-900">{u.usuario}</span>
      ),
    },
    {
      clave: "rol",
      encabezado: "Rol",
      celda: (u) => <Insignia tono="neutro" texto={textoOGuion(u.rol)} />,
    },
  ];

  // La ruta devuelve todas las cuentas de una vez; la tabla las reparte.
  const cuentas = datos ?? [];
  const pagina_actual = cuentas.slice(
    (pagina - 1) * POR_PAGINA,
    pagina * POR_PAGINA,
  );

  if (cargando) return <SkeletonTabla columnas={3} filas={5} />;
  if (error) return <Alerta error={error} alReintentar={recargar} />;

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <p className="text-sm text-tinta-suave">
          Las contraseñas se guardan con bcrypt; el backend nunca devuelve el hash.
        </p>
        <button type="button" className={BOTON.primario} onClick={() => setAlta(true)}>
          Nueva cuenta
        </button>
      </div>

      <Tabla
        columnas={columnas}
        filas={pagina_actual}
        claveFila={(u) => u.usuario}
        titulo="Cuentas registradas"
        pie={
          <Paginador
            pagina={pagina}
            porPagina={POR_PAGINA}
            recibidas={pagina_actual.length}
            alCambiar={setPagina}
          />
        }
      />

      <ModalAltaUsuario
        abierto={alta}
        alCerrar={() => setAlta(false)}
        alGuardar={() => {
          notificar("exito", "Cuenta guardada", "La cuenta quedó registrada.");
          recargar();
        }}
      />

      <ModalContrasena
        cuenta={cuenta}
        alCerrar={() => setCuenta(null)}
        alGuardar={(usuario) =>
          notificar("exito", "Contraseña actualizada", `Se restableció la de ${usuario}.`)
        }
      />
    </section>
  );
}

function ModalAltaUsuario({
  abierto,
  alCerrar,
  alGuardar,
}: {
  abierto: boolean;
  alCerrar: () => void;
  alGuardar: () => void;
}) {
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [rol, setRol] = useState<string>(ROLES[0]);
  const accion = useAccion(() => guardarUsuario(usuario, contrasena, rol));

  const cerrar = () => {
    accion.limpiarError();
    setUsuario("");
    setContrasena("");
    alCerrar();
  };

  const enviar = async () => {
    if (await accion.ejecutar()) {
      alGuardar();
      cerrar();
    }
  };

  const incompleto = usuario.trim().length < 3 || contrasena.length < 4;

  return (
    <Modal
      abierto={abierto}
      titulo="Nueva cuenta de acceso"
      descripcion="Si la cuenta ya existe, se actualizan su contraseña y su rol."
      alCerrar={cerrar}
      pie={
        <>
          <button type="button" className={BOTON.neutro} onClick={cerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className={BOTON.primario}
            disabled={accion.enviando || incompleto}
            onClick={enviar}
          >
            {accion.enviando && <Girador />}
            Guardar cuenta
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <label className="block">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Usuario (correo)
          </span>
          <input
            type="email"
            value={usuario}
            onChange={(evento) => setUsuario(evento.target.value)}
            className={`mt-1.5 ${CAMPO}`}
          />
        </label>

        <label className="block">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Contraseña
          </span>
          <input
            type="password"
            autoComplete="new-password"
            value={contrasena}
            onChange={(evento) => setContrasena(evento.target.value)}
            className={`mt-1.5 ${CAMPO}`}
          />
        </label>

        <label className="block">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Rol
          </span>
          <select
            value={rol}
            onChange={(evento) => setRol(evento.target.value)}
            className={`mt-1.5 ${CAMPO}`}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        {accion.error && <Alerta error={accion.error} />}
      </div>
    </Modal>
  );
}

function ModalContrasena({
  cuenta,
  alCerrar,
  alGuardar,
}: {
  cuenta: UsuarioCuenta | null;
  alCerrar: () => void;
  alGuardar: (usuario: string) => void;
}) {
  const [contrasena, setContrasena] = useState("");
  const accion = useAccion(() => cambiarContrasena(cuenta?.usuario ?? "", contrasena));

  const cerrar = () => {
    accion.limpiarError();
    setContrasena("");
    alCerrar();
  };

  const enviar = async () => {
    const actualizada = await accion.ejecutar();
    if (actualizada) {
      alGuardar(actualizada);
      cerrar();
    }
  };

  return (
    <Modal
      abierto={cuenta !== null}
      titulo="Restablecer contraseña"
      descripcion={cuenta ? `Cuenta ${cuenta.usuario}` : undefined}
      alCerrar={cerrar}
      pie={
        <>
          <button type="button" className={BOTON.neutro} onClick={cerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className={BOTON.primario}
            disabled={accion.enviando || contrasena.length < 4}
            onClick={enviar}
          >
            {accion.enviando && <Girador />}
            Actualizar
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <label className="block">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Nueva contraseña
          </span>
          <input
            type="password"
            autoComplete="new-password"
            value={contrasena}
            onChange={(evento) => setContrasena(evento.target.value)}
            className={`mt-1.5 ${CAMPO}`}
          />
        </label>

        {accion.error && <Alerta error={accion.error} />}
      </div>
    </Modal>
  );
}
