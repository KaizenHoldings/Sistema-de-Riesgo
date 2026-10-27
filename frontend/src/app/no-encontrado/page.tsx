import Link from "next/link";

/**
 * Pantalla de recurso inexistente.
 *
 * Vive como página propia, y no solo como `not-found.tsx`, porque el middleware
 * reescribe hacia ella para poder acompañarla del estado 404.
 */
export default function NoEncontradoPage() {
  return (
    <div className="mx-auto max-w-lg py-16 text-center">
      <p className="text-sm font-semibold tracking-wider text-kaizen-600 uppercase">
        Error 404
      </p>
      <h1 className="mt-3 text-2xl font-bold text-kaizen-900">
        La dirección no corresponde a ningún expediente
      </h1>
      <p className="mt-3 text-sm text-tinta-suave">
        Compruebe la línea de producto y el número de expediente, o vuelva a la
        bandeja para localizarlo desde el listado.
      </p>
      <Link
        href="/evaluations"
        className="mt-6 inline-flex rounded-lg bg-kaizen-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-kaizen-900"
      >
        Volver a la bandeja
      </Link>
    </div>
  );
}
