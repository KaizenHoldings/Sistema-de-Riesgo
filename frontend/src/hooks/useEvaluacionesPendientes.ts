"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/utils/apiClient";
import { useSesion } from "@/components/providers/ProveedorSesion";

interface ConteoPendientes {
  total: number;
  corp: number;
  auto: number;
}

export function useEvaluacionesPendientes() {
  const { sesion } = useSesion();
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!sesion) return;

    let cancelado = false;

    const consultar = () => {
      apiClient.get<ConteoPendientes>("/api/v1/workflow/pendientes/conteo")
        .then((res) => {
          if (!cancelado) {
            setTotal(res.total ?? 0);
          }
        })
        .catch(() => {
          // Si falla la petición se mantiene el valor previo
        });
    };

    consultar();
    const intervalo = setInterval(consultar, 20000);

    return () => {
      cancelado = true;
      clearInterval(intervalo);
    };
  }, [sesion]);

  return {
    total: sesion ? total : 0,
    hayPendientes: Boolean(sesion && total > 0),
  };
}
