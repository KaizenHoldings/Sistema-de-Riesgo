/**
 * Esqueletos de carga.
 *
 * Se prefieren a un indicador giratorio porque reservan la altura definitiva del
 * bloque: la tabla no salta cuando llegan los datos y la lectura no se
 * interrumpe.
 */

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded bg-neutro-fondo ${className}`} aria-hidden />
  );
}

/** Marcador de una fila de tarjetas de métrica. */
export function SkeletonMetricas({ tarjetas = 4 }: { tarjetas?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: tarjetas }, (_, i) => (
        <div
          key={i}
          className="rounded-xl border border-borde bg-white p-5 shadow-sm"
        >
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-4 h-7 w-32" />
          <Skeleton className="mt-3 h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

/** Marcador de una tabla, con el mismo número de columnas que la definitiva. */
export function SkeletonTabla({
  filas = 6,
  columnas = 5,
}: {
  filas?: number;
  columnas?: number;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-borde bg-white shadow-sm">
      <div className="border-b border-borde bg-kaizen-900/5 px-5 py-3">
        <Skeleton className="h-3 w-40" />
      </div>
      <div className="divide-y divide-borde">
        {Array.from({ length: filas }, (_, f) => (
          <div key={f} className="flex items-center gap-4 px-5 py-4">
            {Array.from({ length: columnas }, (_, c) => (
              <Skeleton
                key={c}
                className={`h-4 ${c === 0 ? "w-10" : "flex-1"}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Indicador giratorio para acciones puntuales, no para cargas de página. */
export function Girador({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-kaizen-100 border-t-kaizen-600 ${className}`}
      role="progressbar"
      aria-label="Cargando"
    />
  );
}
