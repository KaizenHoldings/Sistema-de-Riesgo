import { notFound } from "next/navigation";

import { FichaCliente } from "@/components/clientes/FichaCliente";

/** Ficha de un cliente. Valida el identificador antes de montar la vista. */
export default async function ClientePage({ params }: PageProps<"/clients/[id]">) {
  const { id } = await params;
  const cliId = Number(id);
  if (!Number.isInteger(cliId) || cliId <= 0) notFound();

  return <FichaCliente cliId={cliId} />;
}
