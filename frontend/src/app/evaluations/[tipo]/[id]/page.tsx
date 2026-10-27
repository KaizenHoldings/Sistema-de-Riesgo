import { notFound } from "next/navigation";

import { FichaExpediente } from "@/components/evaluaciones/FichaExpediente";
import { PanelAprobacion } from "@/components/sections/PanelAprobacion";
import type { TipoExpediente } from "@/types/api";

/**
 * Expediente en evaluación.
 *
 * Componente de servidor: valida los parámetros de la ruta y compone la página
 * con dos piezas de cliente —el resumen y el panel del circuito—, que son las
 * que necesitan estado. Un tipo que no sea `corp` o `auto`, o un identificador
 * que no sea un número, es una URL inventada y se responde con 404.
 */
export default async function FichaPage({
  params,
}: PageProps<"/evaluations/[tipo]/[id]">) {
  const { tipo, id } = await params;

  if (tipo !== "corp" && tipo !== "auto") notFound();

  const expId = Number(id);
  if (!Number.isInteger(expId) || expId <= 0) notFound();

  return (
    <>
      <FichaExpediente tipo={tipo as TipoExpediente} expId={expId} />
      <PanelAprobacion tipo={tipo as TipoExpediente} expId={expId} />
    </>
  );
}
