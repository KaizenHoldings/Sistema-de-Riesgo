# KFG Risk Architect — línea base de arquitectura actual

## Alcance y estado observado

Este documento describe el árbol de trabajo observado el 1 de septiembre de 2026. La aplicación está desacoplada en un backend FastAPI dentro de `backend/` y un frontend Next.js dentro de `frontend/`. La interfaz Python/Streamlit ya no es el punto de entrada activo; los scripts operativos de la raíz son `run_backend.sh` y `run_frontend.sh`. El inventario encuentra 56 operaciones declaradas mediante routers FastAPI, más `GET /health`, y nueve páginas del App Router de Next.js. Esta es una línea base descriptiva del código actual, no una especificación deseada.

## Estructura del repositorio

La estructura relevante de la raíz es la siguiente. `public/`, `newversion/`, `.streamlit/` y `Calculos_KFG_Risk.html` permanecen como artefactos heredados o auxiliares; la aplicación desacoplada se concentra en `backend/` y `frontend/`.

```text
KfgRisk/
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── auth_routes.py
│   │   │   ├── client_routes.py
│   │   │   ├── document_routes.py
│   │   │   ├── application_routes.py
│   │   │   ├── workflow_routes.py
│   │   │   ├── risk_routes.py
│   │   │   ├── amortization_routes.py
│   │   │   ├── collection_routes.py
│   │   │   ├── system_routes.py
│   │   │   ├── report_routes.py
│   │   │   └── _errores.py
│   │   └── schemas/
│   │       ├── base.py
│   │       ├── cliente.py
│   │       ├── expediente.py
│   │       ├── cobranza.py
│   │       ├── workflow.py
│   │       ├── risk_schemas.py
│   │       └── sistema.py
│   ├── database/
│   │   ├── db_core_sqlserver.py
│   │   ├── daos_sqlserver.py
│   │   └── models.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── security_service.py
│   │   ├── workflow_service.py
│   │   ├── risk_score_service.py
│   │   ├── risk_service.py
│   │   ├── document_service.py
│   │   ├── storage_service.py
│   │   ├── sharepoint_service.py
│   │   ├── template_service.py
│   │   └── metrics_service.py
│   ├── templates/
│   │   ├── _styles.html
│   │   ├── aging_table.html
│   │   ├── callout.html
│   │   ├── client_card.html
│   │   ├── client_row.html
│   │   ├── doc_row.html
│   │   ├── doc_status.html
│   │   ├── expediente_card.html
│   │   ├── kyc_progress.html
│   │   ├── loader.html
│   │   ├── repo_header.html
│   │   └── status_badge.html
│   ├── clients/                 # repositorio local de documentos; datos runtime
│   ├── tests/test_auth_service.py
│   ├── scratch/
│   ├── create_user.sql
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── business/workflows/
│   │   ├── components/
│   │   ├── data/workflowRepository.ts
│   │   ├── hooks/
│   │   ├── types/api.ts
│   │   ├── utils/
│   │   └── middleware.ts
│   ├── next.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── eslint.config.mjs
│   ├── postcss.config.mjs
│   └── .env.example
├── run_backend.sh
└── run_frontend.sh
```

## Backend FastAPI

`backend/api/main.py` crea una instancia `FastAPI` titulada `KFG Risk Architect API`, versión `1.1.0`, y registra, en este orden, `risk_routes`, `amortization_routes`, `auth_routes`, `client_routes`, `application_routes`, `collection_routes`, `workflow_routes`, `system_routes`, `document_routes` y `report_routes`. No hay middleware CORS configurado. La comprobación `GET /health` responde `{"estado": "ok", "version": "1.1.0"}` sin consultar la base. FastAPI aporta además sus rutas automáticas `/docs`, `/redoc` y `/openapi.json`, que no forman parte del conteo de 57 operaciones de aplicación.

### Contratos Pydantic

`api/schemas/base.py` define `ModeloKFG`, la base común de Pydantic, junto con los aliases de tipos para texto, enteros, números y dinero. `cliente.py` contiene `Cliente`, con identidad, contacto, representante, checklist serializado y trazabilidad KYC, y `DocumentoCliente`, con nombre lógico, archivo, carpeta y estado SharePoint. `expediente.py` separa `ExpedienteBase` de `ExpedienteCorporativo` y `ExpedienteAutomotriz`: la base agrupa monto, moneda, firmas, AML, riesgo, dictamen, pricing y cobranza; el corporativo añade RIF, balance, garantías, DSCR y margen EBITDA; el automotriz añade identidad, empleo, vehículo, seguro, prenda, ingreso, gastos y DTI. `cobranza.py` declara `PlanPago`, `GestionCobranza` y `PagoRecibido`; `workflow.py` declara `TareaWorkflow`; `sistema.py` declara las respuestas `Usuario` y `ConfigParametro`.

`risk_schemas.py` concentra los contratos matemáticos. `PesosCorporativos` y `PesosAutomotrices` parametrizan scoring y pricing; `BalanceCorporativo`, `ScoringCorporativoIn`, `ScoringAutomotrizIn`, `IndicadoresIn` y `AltmanIn` validan entradas financieras; `AmortizacionIn` y `AmortizacionPersistirIn` validan monto, tasa, plazo, fecha, expediente y tipo; `CuotaOut` y `PlanAmortizacionOut` serializan el resultado del plan francés. Los cuerpos pequeños específicos de una ruta —`TokenResponse`, `Certificacion`, `Justificacion`, `Devolucion`, `Dictamen`, `CambioParametro`, `AltaUsuario`, `CambioContrasena`, `MarcasChecklist` y `AprobacionKyc`— están definidos junto a sus routers en lugar de `api/schemas/`.

### Endpoints activos

Autenticación expone `POST /token` en `auth_routes.py`. Recibe `OAuth2PasswordRequestForm` (`username` y `password` como `application/x-www-form-urlencoded`), consulta `UsuarioDAO.get_by_credentials` y devuelve `TokenResponse {access_token, token_type}` o 401. `GET /health`, definido en `main.py`, es público y no toca SQL Server.

Clientes usa el prefijo `/api/v1/clientes`. `GET /api/v1/clientes` lista con `pagina` (mínimo 1), `por_pagina` (1–200), `nombre`, `tipo` y `kyc_status`; `GET /api/v1/clientes/{cli_id}` obtiene la ficha; `POST /api/v1/clientes` crea un prospecto desde `Cliente`; `PUT /api/v1/clientes/{cli_id}/kyc?estado=...` cambia el estado; `PUT /api/v1/clientes/{cli_id}/observaciones?observaciones=...` cambia observaciones; `GET /api/v1/clientes/{cli_id}/documentos` devuelve `DocumentoCliente[]`; y `PUT /api/v1/clientes/documentos/{doc_id}/sincronizacion?estado=...` cambia el estado de sincronización. Estas operaciones pertenecen a `client_routes.py` y actualmente no declaran dependencia JWT.

Documentos comparte el prefijo `/api/v1/clientes` desde `document_routes.py`. `GET /api/v1/clientes/{cli_id}/checklist` obtiene requisitos y cobertura; `PUT /api/v1/clientes/{cli_id}/checklist` guarda `MarcasChecklist`; `POST /api/v1/clientes/{cli_id}/documentos` recibe multipart con `doc_name` y `archivo`; `GET /api/v1/clientes/{cli_id}/documentos/{doc_id}/descargar` entrega el binario; `POST /api/v1/clientes/{cli_id}/documentos/{doc_id}/sincronizar` lo envía a SharePoint; y `POST /api/v1/clientes/{cli_id}/kyc/aprobar` cierra KYC con `AprobacionKyc`. Todas requieren `get_current_user`; aprobar KYC requiere además uno de los roles `Compliance` o `Superadmin` mediante `require_role`.

Expedientes usa `/api/v1/expedientes` desde `application_routes.py`. Para corporativos existen `GET /corporativos`, `GET /corporativos/resumen`, `GET /corporativos/{exp_id}`, `POST /corporativos` y `DELETE /corporativos/{exp_id}`; para automotrices existen los equivalentes `GET /automotrices`, `GET /automotrices/resumen`, `GET /automotrices/{exp_id}`, `POST /automotrices` y `DELETE /automotrices/{exp_id}`. Las listas aceptan `pagina`, `por_pagina`, `dictamen`, `cliente` y `firmas_completas`; los `DELETE` son bajas lógicas. El alta nace en Cumplimiento. Estas rutas no declaran autenticación en el estado actual.

Workflow usa `/api/v1/workflow` desde `workflow_routes.py`, con `{tipo}` restringido a `corp|auto`. `GET /{tipo}/{exp_id}/estado` devuelve estado, dictamen y firmas; `GET /{tipo}/{exp_id}/tareas?estado=...` devuelve tareas. Las mutaciones son `POST /{tipo}/{exp_id}/cumplimiento/certificar` con `Certificacion`, `POST /{tipo}/{exp_id}/cumplimiento/observar` y `POST /{tipo}/{exp_id}/cumplimiento/rechazar` con `Justificacion`, `POST /{tipo}/{exp_id}/legal` y `POST /{tipo}/{exp_id}/riesgo` con diccionarios de campos específicos de la línea, `POST /{tipo}/{exp_id}/dictamen` con `Dictamen`, `POST /{tipo}/{exp_id}/devolver` con `Devolucion` y `POST /{tipo}/{exp_id}/rechazar` con `Justificacion`. El router traduce `ExpedienteNoEncontrado` a 404, `TransicionInvalida` a 409 y `DatosInsuficientes` a 422 mediante `_errores.py`; los cuerpos incompatibles de Legal o Riesgo también pasan a 422. Las mutaciones hacen rollback ante error de dominio y commit al completar. Ninguna ruta de este router declara todavía dependencia JWT o de rol.

Riesgo usa `/api/v1/risk` desde `risk_routes.py`. `POST /scoring/corporativo` recibe `ScoringCorporativoIn` y devuelve DSCR, margen EBITDA, scores parciales y final, tasa sugerida, indicadores y Altman; `POST /scoring/automotriz` recibe `ScoringAutomotrizIn` y devuelve ingreso libre, DTI, PTI, scores, tasa y clasificación; `POST /indicadores` recibe `IndicadoresIn` y calcula la batería financiera con fórmulas y semáforos; `POST /altman` recibe `AltmanIn` y calcula el Z-Score privado con componentes y zona. Son operaciones públicas en la configuración actual.

Amortización usa `/api/v1/amortization` desde `amortization_routes.py`. `POST /calculate` recibe `AmortizacionIn`, ejecuta el plan francés sin sesión ni escritura y devuelve `PlanAmortizacionOut`; `POST /persist` recibe `AmortizacionPersistirIn`, calcula, reemplaza el plan anterior y persiste todas las cuotas en una sola sesión, con commit o rollback. Estas operaciones no declaran autenticación.

Cobranza usa `/api/v1/cobranza` desde `collection_routes.py`. `GET /planes/{tipo}/{exp_id}` obtiene el plan; `GET /cuotas` pagina por `pagina`, `por_pagina`, `expediente_id`, `tipo` y `estado`; `PUT /cuotas/{plan_id}/pagada` marca una cuota. `GET /indicadores/aging` acepta `fecha_referencia`; `GET /indicadores/vencimientos` añade `dias_proximos` entre 1 y 365; `GET /indicadores/flujo` exige `fecha_desde` y `fecha_hasta`; `GET /vencidos` devuelve el detalle vencido. `GET /gestiones` pagina por expediente y tipo; `POST /gestiones` recibe `GestionCobranza`; `POST /pagos` recibe `PagoRecibido` y exige monto positivo. `tipo` se valida como `corp|auto`. El router no declara dependencia JWT.

Administración usa `/api/v1` desde `system_routes.py` y está reservada a `Superadmin`. `GET /api/v1/config/parametros` lista políticas de scoring; `PUT /api/v1/config/parametros` recibe `CambioParametro[]`, valida claves y actualiza todo atómicamente; `GET /api/v1/usuarios` lista usuario y rol sin hash; `POST /api/v1/usuarios` crea o actualiza una cuenta con `AltaUsuario`; y `PUT /api/v1/usuarios/{usuario}/contrasena` restablece la contraseña con `CambioContrasena`. Los roles admitidos son `Compliance`, `Legal`, `Riesgo`, `Comité`, `Cobranzas` y `Superadmin`.

Reportes usa `/api/v1/reportes` desde `report_routes.py`. `GET /api/v1/reportes/expedientes/{tipo}/{exp_id}/acta`, autenticado con JWT y con `{tipo}` limitado a `corp|auto`, genera un PDF mediante `DocumentReportService`, sanea el nombre `Acta_{cliente}.pdf` y responde como `StreamingResponse` con `Content-Disposition`.

### Autenticación y autorización

`api/security.py` usa PyJWT, `HS256` y una vigencia de ocho horas. La clave se carga desde `JWT_SECRET_KEY`; `_secret_key()` exige un mínimo de 32 caracteres y falla cerrado. `create_access_token()` firma las claims `sub`, `user`, `role`, `iat` y `exp`; `decode_access_token()` exige todas esas claims, fija explícitamente el algoritmo permitido, verifica expiración y comprueba que `sub == user`. Las contraseñas no se comparan en JWT: `UsuarioDAO.get_by_credentials` conserva la comprobación bcrypt de `SecurityService.verify_password`.

`api/dependencies.py` configura `OAuth2PasswordBearer(tokenUrl="/token")`. `get_current_user` extrae el bearer token, valida firma y expiración y devuelve `{user, role}`; un token inválido o vencido produce 401 con `WWW-Authenticate: Bearer`. `require_role(*allowed_roles)` construye dependencias que producen 403 cuando el rol firmado no está permitido. En la línea base, `system_routes.py` aplica `Superadmin`, `document_routes.py` autentica todas sus operaciones y limita aprobación KYC a Compliance/Superadmin, y `report_routes.py` exige autenticación. Los routers de clientes básicos, expedientes, workflow, riesgo, amortización y cobranza no aplican esas dependencias todavía.

### Sesiones SQL Server y capa de datos

`database/db_core_sqlserver.py` carga `DATABASE_URL`, transforma el formato propio `sqlserver://host:port;database=...;user=...;password=...` a `mssql+pyodbc` y respeta `SQL_DRIVER`, con `ODBC Driver 17 for SQL Server` como valor predeterminado. El `engine` global se crea con `pool_pre_ping=True`; `SessionLocal` usa `autoflush=False` y `expire_on_commit=False`. `get_db()` es la dependencia FastAPI que crea una sesión por petición y siempre la cierra, pero delega commit y rollback a la ruta. `sesion_activa(session=None)` permite que los DAOs reutilicen la sesión externa sin cerrarla ni confirmarla, o crea una sesión local que hace commit al salir, rollback ante excepción y close finalmente. `db_action` ejecuta SQL parametrizado dentro de ese contexto. `init_db()` contiene creación e incorporación incremental de tablas y columnas SQL Server, pero `api/main.py` no registra actualmente un evento de startup que lo invoque.

`database/daos_sqlserver.py` es la única implementación activa del acceso a datos y define `UsuarioDAO`, `ConfigParametroDAO`, `ExpedienteCorporativoDAO`, `ExpedienteAutomotrizDAO`, `TareaWorkflowDAO`, `WorkflowCumplimientoDAO`, `ClienteDAO`, `DocumentoClienteDAO`, `PlanPagoDAO`, `GestionCobranzaDAO` y `PagoRecibidoDAO`. Los DAOs aceptan `session=None`, materializan filas como diccionarios y concentran SQL; las guardas del circuito se mantienen fuera de ellos en `WorkflowService`.

### Servicios de negocio

`services/workflow_service.py` es el coordinador del circuito. Define `ErrorFlujo`, `ExpedienteNoEncontrado`, `TransicionInvalida` y `DatosInsuficientes`; consulta estado y tareas; exige Cumplimiento antes de Legal/Riesgo; exige las tres firmas antes de aprobar; certifica, observa o rechaza Cumplimiento; registra Legal y Riesgo; emite dictamen; devuelve a una etapa y rechaza administrativamente. Usa `WorkflowCumplimientoDAO` y `TareaWorkflowDAO` para persistir estado y tareas dentro de la sesión recibida.

`services/risk_score_service.py` contiene las fórmulas de scoring corporativo y automotriz, estrés, DSCR, margen EBITDA, DTI/PTI, indicadores financieros, Altman, semáforos y pricing. `services/risk_service.py` contiene `AmortizationService`, que calcula y persiste el plan francés; también conserva una clase `RiskScoreService` heredada, distinta de la implementación amplia del archivo dedicado. `document_service.py` genera actas corporativas y automotrices con FPDF. `storage_service.py` abstrae repositorio local o SharePoint y sanea rutas; `sharepoint_service.py` obtiene tokens y sube archivos mediante Microsoft Graph; `template_service.py` configura Jinja2 y renderiza los fragmentos de `templates/`; `security_service.py` conserva hash y verificación bcrypt. `auth_service.py` y `metrics_service.py` todavía contienen puentes heredados de Streamlit, aunque la presentación activa es Next.js.

## Frontend Next.js

El frontend usa Next.js `16.3.4`, React `19.2.8`, TypeScript 5, Tailwind CSS 4 y ESLint 9. `src/app/layout.tsx` monta globalmente `ProveedorSesion`, `ProveedorAvisos` y `MarcoApp`; `src/app/page.tsx` redirige `/` a `/dashboard`. Los layouts de `admin`, `clients`, `dashboard`, `evaluations` y `portfolio` envuelven sus páginas con `Protegido`, una guarda de cliente que espera la sesión de navegador y redirige a `/login` si no existe. `src/middleware.ts` valida únicamente los parámetros de `/evaluations/:tipo/:id` y reescribe combinaciones inválidas a `/no-encontrado` con HTTP 404.

### Jerarquía del App Router

```text
src/app/
├── layout.tsx                       # RootLayout: sesión, avisos y MarcoApp
├── page.tsx                         # / -> /dashboard
├── login/page.tsx                   # /login
├── dashboard/
│   ├── layout.tsx                   # Protegido
│   └── page.tsx                     # /dashboard
├── clients/
│   ├── layout.tsx                   # Protegido
│   ├── page.tsx                     # /clients
│   └── [id]/page.tsx                # /clients/:id
├── evaluations/
│   ├── layout.tsx                   # Protegido
│   ├── page.tsx                     # /evaluations
│   └── [tipo]/[id]/page.tsx         # /evaluations/:tipo/:id
├── portfolio/
│   ├── layout.tsx                   # Protegido
│   └── page.tsx                     # /portfolio
├── admin/
│   ├── layout.tsx                   # Protegido
│   └── page.tsx                     # /admin
├── no-encontrado/page.tsx           # destino 404 con marco
└── not-found.tsx                    # fallback notFound()
```

`/login` presenta el formulario institucional y llama a `iniciarSesion`. `/dashboard` combina resúmenes de expedientes corporativos y automotrices con indicadores de vencimiento para mostrar originación, cartera y detalle por dictamen. `/clients` ofrece búsqueda, estado KYC, paginación y enlace a ficha; `/clients/[id]` valida el id y monta `FichaCliente`, que presenta datos, checklist, documentos y aprobación KYC. `/evaluations` lista y filtra ambas líneas; `/evaluations/[tipo]/[id]` monta `FichaExpediente` y `PanelAprobacion`, con las etapas Cumplimiento, Legal, Riesgo y Comité. `/portfolio` presenta vencimientos, aging, cuotas y permite marcar una cuota pagada. `/admin` contiene pestañas de política corporativa, política automotriz y usuarios, con alta y restablecimiento de contraseña.

### Componentes, negocio y acceso a datos

La capa visual se divide por intención. `components/layout/MarcoApp.tsx` exporta `MarcoApp` y `EncabezadoPagina`; `BarraLateral.tsx` fija los enlaces Dashboard, Clientes, Evaluaciones, Cartera y Configuración y muestra usuario, rol, estado del backend y cierre de sesión. `components/providers/ProveedorSesion.tsx` expone `ProveedorSesion` y `useSesion`; `Protegido.tsx` controla únicamente la existencia de sesión. `components/ui/` contiene `Alerta`, `SinResultados`, `Modal`, constantes `BOTON` y `CAMPO`, `Paginador`, `Insignia`, `Firmas`, skeletons, `Girador`, `Tabla`, `TarjetaMetrica`, `ProveedorAvisos` y `useAvisos`.

El dominio de clientes usa `ChecklistDocumental` y `FichaCliente`. Evaluaciones usa `FichaExpediente` y los modales `ModalConfirmacion`, `ModalJustificacion` y `ModalAprobacion`. `components/sections/PanelAprobacion.tsx` orquesta `FlujoAprobacion`, `FormularioCumplimiento`, `FormularioLegal`, `FormularioRiesgo` y `FormularioComiteBI`; `campos.tsx` centraliza controles reutilizables. La lógica de flujo no está incrustada en las páginas: `business/workflows/approvalWorkflow.ts` deriva etapa, firmas, pasos y acciones; `business/workflows/service.ts` valida formularios, normaliza errores y ejecuta transiciones; `data/workflowRepository.ts` es el único repositorio que conoce las URLs del workflow. Los contratos de ese dominio viven en `business/workflows/types.ts`, mientras `types/api.ts` representa respuestas generales del backend.

Los hooks son la capa de consulta y mutación para páginas y componentes. `useApiQuery` maneja cancelación, recarga, filtros y errores; `useAccion` maneja envíos; `useClientes`, `useExpedientes`, `useCartera`, `useDocumentos`, `useWorkflow`, `useAdmin` y `useSalud` encapsulan sus familias de endpoints. Los helpers `utils/estados.ts`, `format.ts` y `descargas.ts` se ocupan de semáforos, presentación y blobs.

### Cliente HTTP, proxy y sesión del navegador

`src/utils/apiClient.ts` es el único cliente HTTP general. `API_BASE_URL` usa `NEXT_PUBLIC_API_URL` si está configurada; de otro modo usa el origen del navegador y, durante render de servidor, `http://127.0.0.1:3000`. `apiClient.get`, `post`, `put` y `delete` envían JSON, `postForm` envía el formulario OAuth2, `postMultipart` carga archivos sin fijar manualmente el boundary y `descargar` obtiene blobs protegidos. Todas las operaciones salvo el formulario de login consultan `leerToken()` e incorporan `Authorization: Bearer <JWT>` cuando hay sesión. Un 401 limpia la sesión; 404, 409 y 422 se normalizan en `ApiError`, incluyendo el detalle por campo de Pydantic; errores de red reciben estado lógico 0.

`next.config.ts` evita CORS por diseño: reescribe `/api/:ruta*` a `${BACKEND_ORIGIN}/api/:ruta*`, `/health` a `${BACKEND_ORIGIN}/health` y `/token` a `${BACKEND_ORIGIN}/token`, usando `http://127.0.0.1:8000` como backend predeterminado. `NEXT_PUBLIC_API_URL` solo debe rellenarse si el navegador hablará con otro origen y el backend incorpora CORS.

`utils/auth.ts` solicita `/token` y decodifica localmente las claims `user` y `role` para rotular la interfaz; esa decodificación no verifica la firma y el propio archivo deja la autorización real al backend. `utils/session.ts` guarda `{token, usuario, rol}` en memoria y `sessionStorage` bajo `kfg.sesion`, no en `localStorage`, y publica cambios a React. `ProveedorSesion` usa `useSyncExternalStore` para hidratar esa sesión. La representación condicional por rol es limitada en la línea base: los layouts solo comprueban que exista una sesión, `BarraLateral` muestra los mismos módulos a todos y `PanelAprobacion` habilita pestañas según estado del expediente, no según rol. La autorización efectiva por rol está en las dependencias FastAPI donde fueron aplicadas; por ejemplo, `/admin` se puede montar para cualquier sesión, pero sus llamadas reciben 403 salvo que el JWT diga `Superadmin`.

## Ejecución y contenedores

No existe en el árbol actual ningún `docker-compose.yml`, `docker-compose.yaml`, `Dockerfile`, variante de Dockerfile ni `.dockerignore`. Por tanto, no hay servicios, redes, volúmenes, healthchecks, imágenes o variables Docker activas que puedan documentarse; cualquier referencia futura a “la orquestación encontrada” debe considerar esta ausencia como parte de la línea base.

La orquestación vigente es manual mediante scripts shell. `run_backend.sh` cambia a `backend/`, avisa si `JWT_SECRET_KEY` no está en el entorno ni en `backend/.env`, y ejecuta `python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload`. `run_frontend.sh` cambia a `frontend/` y ejecuta `npm run dev`, que levanta Next en el puerto 3000. El servidor Next usa `BACKEND_ORIGIN=http://127.0.0.1:8000` por defecto para el proxy. `backend/.env.example` documenta administrador inicial, `DATABASE_URL`, `SQL_DRIVER`, `STORAGE_PROVIDER` y variables Graph/SharePoint, aunque actualmente no incluye la clave JWT que el backend exige; `frontend/.env.example` documenta `BACKEND_ORIGIN` y `NEXT_PUBLIC_API_URL`.

## Fronteras arquitectónicas relevantes

La dirección de dependencias activa es navegador → `apiClient` → rewrites de Next → routers FastAPI → servicios de negocio → DAOs → SQL Server. Los cálculos financieros permanecen en servicios Python y el frontend solo envía entradas y presenta resultados. Las reglas de workflow se validan dos veces con responsabilidades distintas: TypeScript deriva acciones para evitar ofrecer operaciones imposibles, pero `WorkflowService` es la autoridad y puede responder 404/409/422. Las transacciones se gobiernan en las rutas FastAPI al compartir una sesión entre DAOs y servicios. Los archivos se abstraen mediante `StorageService`, con inventario SQL y proveedor local o SharePoint. La autenticación es JWT, pero su cobertura no es global: la presencia del bearer token en el cliente no implica que cada endpoint del backend lo exija.
