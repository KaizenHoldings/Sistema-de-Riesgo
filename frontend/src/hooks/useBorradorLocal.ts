"use client";

/**
 * Borrador local de un formulario, persistido en `localStorage`.
 *
 * Tres fases, en este orden:
 *
 * 1. **Restauración.** Tras el montaje se lee el borrador y se entrega a
 *    `aplicar`. La lectura se difiere a una microtarea dentro del efecto: en el
 *    servidor no hay `localStorage`, y leerlo durante el render provocaría un
 *    desajuste de hidratación. La microtarea corre antes del pintado, así que no
 *    se ve un parpadeo de campos vacíos.
 * 2. **Autoguardado.** Cada cambio del estado se escribe con un breve retardo,
 *    para no serializar el formulario entero en cada pulsación.
 * 3. **Descarte.** `descartar()` borra el borrador; se llama tras un envío con
 *    éxito, cuando lo registrado en el backend ya es la fuente de verdad.
 *
 * El guardado no empieza hasta que la restauración ha terminado. Sin esa guarda,
 * el primer autoguardado escribiría el estado inicial vacío encima del borrador
 * antes de llegar a leerlo.
 */

import { useCallback, useEffect, useRef, useState } from "react";

/** Versión del sobre. Un borrador de otra versión se ignora en vez de romper. */
const VERSION = 1;
const RETARDO_GUARDADO_MS = 400;

interface Sobre<T> {
  v: number;
  guardado: string;
  datos: T;
}

export interface EstadoBorrador {
  /** Cierto cuando la restauración ha terminado y el autoguardado está activo. */
  listo: boolean;
  /** Cierto si al montar se recuperó un borrador previo. */
  restaurado: boolean;
  /** Momento del último guardado, o nulo si aún no se ha guardado nada. */
  guardadoEn: Date | null;
  descartar: () => void;
  /**
   * Cede ante una fuente más fiable —la base de datos—: borra el borrador y no
   * guarda el estado que produzca el siguiente render, que es el de esa fuente.
   * Se llama justo antes de aplicar sus datos.
   */
  adoptar: () => void;
}

function leer<T>(clave: string): Sobre<T> | null {
  try {
    const crudo = window.localStorage.getItem(clave);
    if (!crudo) return null;
    const sobre = JSON.parse(crudo) as Partial<Sobre<T>>;
    if (sobre?.v !== VERSION || sobre.datos === undefined) return null;
    return sobre as Sobre<T>;
  } catch {
    // Almacenamiento bloqueado o contenido corrupto: se empieza de cero.
    return null;
  }
}

export function useBorradorLocal<T>(
  clave: string,
  estado: T,
  aplicar: (datos: T) => void,
): EstadoBorrador {
  const [listo, setListo] = useState(false);
  const [restaurado, setRestaurado] = useState(false);
  const [guardadoEn, setGuardadoEn] = useState<Date | null>(null);

  // `aplicar` suele ser una función nueva en cada render; se guarda en una
  // referencia desde un efecto para que la restauración dependa solo de la clave.
  const aplicarRef = useRef(aplicar);
  useEffect(() => {
    aplicarRef.current = aplicar;
  });

  const listoRef = useRef(false);
  // La pasada que activa el guardado lleva el estado recién restaurado (o el
  // inicial): no hay nada tecleado que guardar, y escribirlo crearía un borrador
  // vacío por cada expediente que solo se abrió.
  const omitirPrimeraRef = useRef(false);
  const descartadoRef = useRef<T | null>(null);
  const temporizadorRef = useRef<number | null>(null);

  // 1. Restauración, una vez por clave.
  useEffect(() => {
    let vigente = true;
    listoRef.current = false;

    queueMicrotask(() => {
      if (!vigente) return;
      const sobre = leer<T>(clave);
      if (sobre) {
        aplicarRef.current(sobre.datos);
        setRestaurado(true);
        setGuardadoEn(new Date(sobre.guardado));
      }
      listoRef.current = true;
      omitirPrimeraRef.current = true;
      setListo(true);
    });

    return () => {
      vigente = false;
    };
  }, [clave]);

  // 2. Autoguardado con retardo.
  useEffect(() => {
    if (!listoRef.current) return;
    if (omitirPrimeraRef.current) {
      omitirPrimeraRef.current = false;
      return;
    }
    // Tras descartar, el mismo estado no debe volver a escribirse; una edición
    // posterior sí abre un borrador nuevo.
    if (descartadoRef.current === estado) return;
    descartadoRef.current = null;

    temporizadorRef.current = window.setTimeout(() => {
      try {
        const sobre: Sobre<T> = {
          v: VERSION,
          guardado: new Date().toISOString(),
          datos: estado,
        };
        window.localStorage.setItem(clave, JSON.stringify(sobre));
        setGuardadoEn(new Date(sobre.guardado));
      } catch {
        // Cuota agotada o almacenamiento bloqueado: el formulario sigue en memoria.
      }
    }, RETARDO_GUARDADO_MS);

    return () => {
      if (temporizadorRef.current !== null) {
        window.clearTimeout(temporizadorRef.current);
      }
    };
  }, [clave, estado, listo]);

  // 3. Descarte explícito.
  const descartar = useCallback(() => {
    if (temporizadorRef.current !== null) {
      window.clearTimeout(temporizadorRef.current);
      temporizadorRef.current = null;
    }
    descartadoRef.current = estado;
    try {
      window.localStorage.removeItem(clave);
    } catch {
      // Nada que borrar si el almacenamiento no está disponible.
    }
    setGuardadoEn(null);
    setRestaurado(false);
  }, [clave, estado]);

  // 4. Cesión a otra fuente.
  const adoptar = useCallback(() => {
    if (temporizadorRef.current !== null) {
      window.clearTimeout(temporizadorRef.current);
      temporizadorRef.current = null;
    }
    omitirPrimeraRef.current = true;
    try {
      window.localStorage.removeItem(clave);
    } catch {
      // Nada que borrar si el almacenamiento no está disponible.
    }
    setGuardadoEn(null);
    setRestaurado(false);
  }, [clave]);

  return { listo, restaurado, guardadoEn, descartar, adoptar };
}

/** Clave única por expediente: la línea de producto evita cruzar corp/5 con auto/5. */
export function claveBorradorRiesgo(tipo: string, expId: number): string {
  return `kfg_risk_draft_${tipo}_${expId}`;
}

/**
 * Funde un borrador sobre el estado base conservando solo lo que encaja.
 *
 * Solo se toman las claves que el estado actual conoce y con el mismo tipo
 * primitivo. Un borrador guardado con una versión anterior del formulario —con
 * campos que ya no existen o que cambiaron de tipo— no puede así colar valores
 * que la derivación no espera.
 */
export function fundirConocidas<T extends Record<string, unknown>>(
  base: T,
  borrador: unknown,
): T {
  if (!borrador || typeof borrador !== "object") return base;
  const fuente = borrador as Record<string, unknown>;
  const resultado = { ...base };
  for (const clave of Object.keys(base) as Array<keyof T>) {
    const valor = fuente[clave as string];
    if (valor !== undefined && typeof valor === typeof base[clave]) {
      resultado[clave] = valor as T[keyof T];
    }
  }
  return resultado;
}
