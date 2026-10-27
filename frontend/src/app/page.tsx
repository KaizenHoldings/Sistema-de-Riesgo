import { redirect } from "next/navigation";

/** La raíz no tiene contenido propio: el tablero es la entrada de la aplicación. */
export default function Inicio() {
  redirect("/dashboard");
}
