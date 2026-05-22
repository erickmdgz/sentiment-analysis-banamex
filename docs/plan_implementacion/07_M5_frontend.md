---
tipo: m-doc
modulo: M5
estado: completado
paquete: web
pr: 5
tags:
  - plan-implementacion
  - modulo-m5
---

# M5 — Frontend (SPA React)

## Responsabilidad

M5 implementa la SPA React + Vite + TypeScript que consume la API HTTP de M4 y materializa las pantallas del Gerente Nacional CX descritas en `docs/propuesta_inicial.md`. Cubre el flujo completo: login (§4 propuesta), upload + validación (§4–§6 propuesta), vista nacional YTD (§7 propuesta), comparación nacional entre meses (§8 propuesta), selector de sucursal (§9 propuesta), vista YTD de sucursal (§10 propuesta), comparación mensual de sucursal (§11 propuesta), y la sección admin POC con distinción visual entre "Vista CX" y "Administración" (§3 propuesta).

El stack está fijado por `00_decisiones_tecnicas.md §2`: React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui + Recharts + TanStack Query + React Router. No se introducen otras librerías de UI (ni MUI, ni Chakra, ni Ant Design, ni Mantine). El estado de servidor lo maneja TanStack Query; no se usa Redux ni Zustand. El cliente HTTP es **generado** a partir de `openapi.json` que M4 publica (`01_contratos §10`). Mientras M4 no exporte el OpenAPI, M5 desarrolla contra **MSW (Mock Service Worker)** con respuestas sintéticas que respetan los DTOs del `01_contratos §4`.

Token JWT en `localStorage.banamex_token` (decisión §2 y §18 de `00_decisiones_tecnicas.md`). Cualquier respuesta 401 dispara logout + redirección a `/login`.

---

## Entregables

- Proyecto Vite + React 18 + TypeScript inicializado en `web/`.
- Tailwind 3.x configurado (`tailwind.config.ts`, `postcss.config.js`, directivas en `src/index.css`).
- shadcn/ui inicializado con primitives: `button`, `card`, `input`, `label`, `table`, `tabs`, `select`, `dialog`, `toast`, `badge`, `skeleton`, `separator`, `scroll-area`, `combobox`.
- React Router con todas las rutas listadas en este documento y consistentes con `01_contratos §1`.
- `Layout` con `Sidebar` de dos secciones visualmente separadas: "Vista CX" y "Administración" (§3 propuesta).
- 7 pantallas implementadas (lista en sección "Pantallas").
- ~15 componentes reutilizables en `web/src/components/*` (lista en "Detalles de implementación").
- Cliente API tipado en `web/src/api/client.ts` (wrapper sobre tipos generados con `openapi-typescript` en `web/src/api/schema.d.ts`).
- TanStack Query inicializado en `web/src/api/queryClient.ts` con `staleTime: 5 * 60 * 1000` (5 min) y `retry: 1`.
- MSW con handlers para **todos** los endpoints declarados en `01_contratos §8`, archivos en `web/src/mocks/handlers.ts`.
- Fixtures determinísticas en `web/src/mocks/fixtures.ts` (mismo input → mismo output) cubriendo: 16 meses (2025-01 … 2026-04), 1,291 sucursales sintéticas, distribución NPS coherente.
- Hook `useAuth()` que expone `login`, `logout`, `isAuthenticated`, `token`, `username`.
- Hook `useBranch()` que extrae `branchId` desde URL params (`useParams`).
- Componentes de estado: `LoadingSkeleton`, `ErrorBoundary`, `Toaster` (shadcn) integrado en el `Layout`.
- `Dockerfile` multistage: `node:20-alpine` para build → `nginx:alpine` para servir `dist/`.
- `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `index.html`, `.gitignore`.
- `README.md` del paquete con instrucciones de instalación, dev server, build, generación del cliente OpenAPI.

---

## Contratos consumidos

- **`openapi.json`** exportado por M4 (`01_contratos §10`). El script `scripts/generate_openapi_client.sh` corre `npx openapi-typescript ../api/openapi.json --output src/api/schema.d.ts` y regenera tipos.
- **DTOs Pydantic** del `01_contratos §4` (`NPSSummary`, `MonthlyTrend`, `CauseBucket`, `StrengthBucket`, `CriticalBranch`, `Rankings`, `SuggestedAction`, `ImpactByCategory`, `Insight`, `WordFrequency`, `RepresentativeComment`, `PersonnelMention`, `NationalYTD`, `BranchYTD`, `MonthlyComparison`, `ValidationSummary`, `CoverageSummary`). Estos DTOs son la **fuente de verdad** del shape de cada respuesta.
- **Endpoints HTTP** listados en `01_contratos §8`. M5 consume todos los listados ahí.
- **Convención de errores** del `01_contratos §9`: respuestas `{detail, code, hint?}`.
- **Mientras M4 no esté listo**: MSW handlers que devuelven respuestas conformes a esos DTOs. Cuando M4 publique `openapi.json`, M5 regenera tipos y desactiva MSW vía `VITE_USE_MOCKS=false`.

---

## Contratos producidos

- **SPA navegable** servida por nginx en el puerto 80 del contenedor `web` (decisión §20 de `00_decisiones_tecnicas.md`).
- **Build estático** en `web/dist/` con bundle único `index.html` + assets hashed.
- **No produce esquemas consumidos por otros módulos**: M5 es terminal en la cadena de contratos.

---

## Estructura de archivos esperada

Subset del `01_contratos §1` correspondiente al paquete `web/`:

```
web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── index.html
├── Dockerfile
├── README.md
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes.tsx
│   ├── index.css                       # directivas tailwind
│   ├── api/
│   │   ├── client.ts                   # wrapper fetch tipado
│   │   ├── schema.d.ts                 # generado de openapi.json
│   │   └── queryClient.ts              # TanStack Query setup
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── UploadPage.tsx
│   │   ├── NationalYTDPage.tsx
│   │   ├── NationalComparePage.tsx
│   │   ├── BranchYTDPage.tsx
│   │   ├── BranchComparePage.tsx
│   │   └── AdminPage.tsx
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── AuthGuard.tsx
│   │   ├── SyntheticTargetsBanner.tsx
│   │   ├── NPSCard.tsx
│   │   ├── DistributionChart.tsx
│   │   ├── TrendChart.tsx
│   │   ├── CausesPanel.tsx
│   │   ├── StrengthsPanel.tsx
│   │   ├── CriticalBranchesTable.tsx
│   │   ├── RankingsPanel.tsx
│   │   ├── ActionsPanel.tsx
│   │   ├── BranchSelector.tsx
│   │   ├── WordsCloud.tsx
│   │   ├── RepresentativeComments.tsx
│   │   ├── PersonnelTable.tsx
│   │   ├── InsightsList.tsx
│   │   ├── MonthSelector.tsx
│   │   └── ui/                         # primitives shadcn
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── useBranch.ts
│   ├── lib/
│   │   ├── format.ts                   # formatNPS, formatPct, formatDate
│   │   └── colors.ts                   # mapeo gap → semáforo
│   └── mocks/
│       ├── browser.ts                  # setupWorker
│       ├── handlers.ts                 # ~30 endpoints
│       └── fixtures.ts                 # data sintética determinística
└── tests/
    ├── useAuth.test.ts
    ├── NPSCard.test.tsx
    ├── DistributionChart.test.tsx
    ├── CausesPanel.test.tsx
    ├── MonthSelector.test.tsx
    ├── BranchSelector.test.tsx
    ├── handlers.test.ts
    └── pages/
        ├── NationalYTDPage.test.tsx
        └── BranchYTDPage.test.tsx
```

---

## Detalles de implementación clave

### Bootstrap del proyecto

```bash
npm create vite@latest web -- --template react-ts
cd web
npm install
npx tailwindcss init -p
npx shadcn-ui@latest init
# style: New York | base color: Neutral | CSS vars: yes
npx shadcn-ui@latest add button card input label table tabs select dialog toast badge skeleton separator scroll-area combobox
npm install @tanstack/react-query @tanstack/react-query-devtools react-router-dom recharts msw zod
npm install -D openapi-typescript vitest @testing-library/react @testing-library/jest-dom jsdom
```

### `tailwind.config.ts`

Paleta extendida con colores semánticos del banco:

```ts
extend: {
  colors: {
    banamex: {
      red: '#dc2626',     // detractor / gap rojo
      amber: '#f59e0b',   // pasivo / gap amarillo
      green: '#16a34a',   // promotor / gap verde
    },
  },
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
  },
}
```

Resto del tema: presets que `shadcn-ui init` deja preconfigurados.

### React Router

`web/src/routes.tsx`:

```tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route element={<AuthGuard><Layout /></AuthGuard>}>
    <Route index element={<Navigate to="/national" replace />} />
    <Route path="/upload" element={<UploadPage />} />
    <Route path="/national" element={<NationalYTDPage />} />
    <Route path="/national/compare" element={<NationalComparePage />} />
    <Route path="/branches/:branchId" element={<BranchYTDPage />} />
    <Route path="/branches/:branchId/compare" element={<BranchComparePage />} />
    <Route path="/admin/*" element={<AdminPage />} />
  </Route>
  <Route path="*" element={<Navigate to="/national" replace />} />
</Routes>
```

### `useAuth`

```ts
// web/src/hooks/useAuth.ts
const TOKEN_KEY = 'banamex_token';

export function useAuth() {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_KEY)
  );

  const login = async (username: string, password: string) => {
    const res = await apiClient.post('/auth/login', { username, password });
    localStorage.setItem(TOKEN_KEY, res.token);
    setToken(res.token);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  };

  const isAuthenticated = () => {
    if (!token) return false;
    try {
      const [, payload] = token.split('.');
      const { exp } = JSON.parse(atob(payload));
      return Date.now() / 1000 < exp;
    } catch { return false; }
  };

  return { token, login, logout, isAuthenticated };
}
```

`AuthGuard` envuelve `Layout` y redirige a `/login` si `!isAuthenticated()`. Decode del JWT solo lee `exp`; cualquier `username/password` es válido en backend (decisión §18 de `00_decisiones_tecnicas.md`).

### Cliente API

Tipos generados a partir de `openapi.json` con `openapi-typescript`:

```bash
# scripts/generate_openapi_client.sh
cd web
npx openapi-typescript ../api/openapi.json --output src/api/schema.d.ts
```

Wrapper en `web/src/api/client.ts`:

```ts
import type { paths } from './schema';

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('banamex_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...opts.headers,
  };
  const res = await fetch(`${import.meta.env.VITE_API_URL}${path}`, { ...opts, headers });
  if (res.status === 401) {
    localStorage.removeItem('banamex_token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error inesperado' }));
    throw new Error(err.detail || 'Error desconocido');
  }
  return res.json();
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
};
```

Hooks TanStack Query por endpoint (ejemplos):

```ts
export const useNationalYTD = () =>
  useQuery({
    queryKey: ['national', 'ytd'],
    queryFn: () => apiClient.get<NationalYTD>('/national/ytd'),
  });

export const useBranchYTD = (branchId: string) =>
  useQuery({
    queryKey: ['branches', branchId, 'ytd'],
    queryFn: () => apiClient.get<BranchYTD>(`/branches/${branchId}/ytd`),
    enabled: !!branchId,
  });
```

### TanStack Query

```ts
// web/src/api/queryClient.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

DevTools solo en dev:

```tsx
{import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
```

Invalidación tras upload (§5 propuesta):

```ts
await apiClient.post('/upload', formData);
queryClient.invalidateQueries({ queryKey: ['national'] });
queryClient.invalidateQueries({ queryKey: ['branches'] });
queryClient.invalidateQueries({ queryKey: ['validation'] });
```

### MSW

`web/src/mocks/browser.ts`:

```ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';
export const worker = setupWorker(...handlers);
```

Arranque condicional en `main.tsx`:

```tsx
async function bootstrap() {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS === 'true') {
    const { worker } = await import('./mocks/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }
  ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
}
bootstrap();
```

`handlers.ts` cubre **todos** los endpoints del `01_contratos §8`: `/auth/login`, `/auth/me`, `/upload`, `/upload/:id/status`, `/validation`, `/validation/coverage`, `/national/ytd`, `/national/trend`, `/national/compare`, `/national/critical-branches`, `/national/rankings`, `/national/causes`, `/national/strengths`, `/national/actions`, `/national/impact`, `/national/insights`, `/national/passive-analysis`, `/branches`, `/branches/:id/ytd`, `/branches/:id/trend`, `/branches/:id/compare`, `/branches/:id/causes`, `/branches/:id/strengths`, `/branches/:id/words`, `/branches/:id/representatives`, `/branches/:id/personnel`, `/branches/:id/actions`, `/branches/:id/insights`, `/admin/files`, `/admin/runs`, `/healthz`.

`fixtures.ts` genera datos determinísticos con `seedrandom` o función pura sobre `branchId`. Garantiza que la misma sucursal devuelva siempre el mismo NPS y los mismos comentarios entre recargas.

### Layout

`Sidebar` (240px ancho fijo, ver §3 propuesta) con dos secciones separadas visualmente por un `Separator`:

- **Vista CX** (icono `User` de lucide-react):
  - Upload (`/upload`)
  - Vista Nacional (`/national`)
  - Comparación Nacional (`/national/compare`)
  - Sucursales (`/branches`)
- **Administración** (icono `Settings`, separador visual encima):
  - Gestión de usuarios (placeholder)
  - Cargas (`/admin/files`)
  - Validación de archivos (`/admin/runs`)
  - Configuración (placeholder)
  - Monitoreo (placeholder)
  - Logs (placeholder)

Topbar con: breadcrumb dinámico, nombre de usuario actual (`useAuth().username`), botón logout.

`SyntheticTargetsBanner` (banner amarillo persistente en cabecera de vistas con brecha) que muestra el texto literal: "Objetivos NPS sintéticos para demo" (decisión §15 de `00_decisiones_tecnicas.md` y §8 de `01_contratos`).

### Componentes reutilizables

- **`NPSCard`**: muestra valor NPS grande + objetivo pequeño + brecha con badge. Colores semafóricos según `gap`: `gap ≥ 0` → verde (`banamex-green`); `-10 < gap < 0` → ámbar (`banamex-amber`); `gap ≤ -10` → rojo (`banamex-red`). Tooltip "Polaridad inferida del NPS del cliente" si aplica (decisión §8 de `00_decisiones_tecnicas.md`).
- **`DistributionChart`**: `PieChart` de Recharts con 3 sectores (Promotor verde, Pasivo ámbar, Detractor rojo). Labels en porcentaje y conteo.
- **`TrendChart`**: `LineChart` de Recharts con eje X mensual (`YYYY-MM`) y eje Y NPS. Muestra hasta 16 puntos (enero 2025 – abril 2026).
- **`CausesPanel`**: lista ordenada descendente por `count`, cada item con barra horizontal proporcional y badges `count` + `pct_of_group`. Color base rojo.
- **`StrengthsPanel`**: idéntico a `CausesPanel` pero color base verde.
- **`CriticalBranchesTable`**: tabla con columnas `branch_id | NPS | brecha | %detractores | condición disparada`. Cada `condition` se muestra como `Badge` (hasta 4 condiciones de `triggered_conditions` por fila). Click en `branch_id` navega a `/branches/:id`.
- **`RankingsPanel`**: `Tabs` con 5 tabs (worst_nps, worst_gap, most_detractors, worsened, improved). Cada tab muestra una tabla con `branch_id | value | label`.
- **`ActionsPanel`**: lista de `SuggestedAction` con badge de `priority` (alta=rojo, media=ámbar, baja=neutral). Muestra `related_bucket` y links a `related_branches`.
- **`BranchSelector`**: `Combobox` shadcn con búsqueda por `branch_id`. Si la lista tiene >100 items, virtualiza con `react-window` (1,291 sucursales). Atajo "Sucursales críticas" arriba de la lista.
- **`WordsCloud`**: por defecto tabla simple `palabra | count`. Si el `WordFrequency[]` viene con campo `group`, ofrece `Tabs` (General / Promotores / Detractores / Mes).
- **`RepresentativeComments`**: cards con `Badge` de `bucket`, `nps_rate`, fecha formateada, y `verbatim` en blockquote.
- **`PersonnelTable`**: tabla con `nombre | polaridad (badge color) | conteo | ejemplo (verbatim truncado)`.
- **`InsightsList`**: cards con icono según `category` (nps / brecha / fortaleza / fricción / personal / comparación / cobertura) usando iconos de lucide-react.
- **`MonthSelector`**: dropdown shadcn `Select` que se llena con `useQuery(['validation'])` y muestra `months_available`. Formato `YYYY-MM` con label castellano (`"enero 2026"`).

---

## Pantallas (especificación detallada)

### 1. Login (`/login`)

Formulario centrado en card shadcn (max-width 400px). Campos:

- `username` (`Input`)
- `password` (`Input type="password"`)
- Botón `Entrar` (`Button` primary)

`onSubmit`: invoca `useAuth().login()`. Cualquier combinación funciona contra el backend (decisión §18 de `00_decisiones_tecnicas.md`).

Tras éxito:
- Redirige a `/upload` si `GET /validation` devuelve `rows_loaded === 0`.
- Redirige a `/national` si ya hay datos cargados.

Footer del card: nota pequeña "Demo del Hackathon Banamex CX — autenticación simulada".

### 2. Upload + Validación (`/upload`, §4–§6 de propuesta)

Header de página: título "Carga de archivos NPS".

- **Drop zone grande** (h-64, dashed border) con texto "Arrastra archivos `.txt` aquí o haz clic para seleccionar". Acepta `multiple`. Activa al click un `<input type="file" accept=".txt" multiple>` oculto.
- **Soporta múltiples archivos a la vez** y carga sucesiva. Cada archivo se sube secuencialmente vía `POST /upload`.
- **Mientras se sube**: progress bar por archivo (`Skeleton` o `Progress`). Estado se obtiene de `GET /upload/{file_id}/status` con polling cada 2s: `parsing → classifying → done | error`.
- **Tras carga**: card por archivo con todos los campos de `ValidationSummary` (§6.1 propuesta):
  - Archivos procesados, registros cargados, nuevos, duplicados ignorados, sucursales detectadas, periodo disponible, meses disponibles, columnas detectadas.
  - Registros válidos / con verbalización vacía / con NPS inválido / sin branch / duplicados / fechas inválidas.
- **Sección "Cobertura de objetivos"** (§6.2 propuesta): card con `CoverageSummary`. Conteos visibles:
  - Sucursales detectadas en encuestas.
  - Sucursales con objetivo configurado.
  - Sucursales detectadas sin objetivo (lista colapsable).
  - Sucursales con objetivo pero sin respuestas (lista colapsable).
  - Objetivos inválidos, objetivos duplicados (si existen).
- **Botón "Continuar a vista nacional"** abajo, navega a `/national` e invalida queries `national/*`, `branches/*`, `validation`.

### 3. Vista nacional YTD (`/national`, §7 de propuesta)

Consume `GET /national/ytd` → `NationalYTD`.

**Header**: título "Vista Nacional Year To Date" + `SyntheticTargetsBanner`.

**Hero** (grid 3 columnas): tres `NPSCard` lado a lado:

- NPS actual nacional (`nps.nps_actual`).
- NPS objetivo nacional (`nps.nps_target`).
- Brecha (`nps.gap`).

Además: total respuestas + total sucursales (texto secundario) + `branches_total` / `branches_with_target` de `NationalYTD`.

**Grid 2 columnas**:
- Izquierda: `DistributionChart` (de `nps.distribution`) + `TrendChart` (de `trend.points`).
- Derecha: `CausesPanel` (top 8 de `causes`) + `StrengthsPanel` (top 8 de `strengths`).

**Sección ancha**: `CriticalBranchesTable` con 10 filas de `critical_branches` (§7.8 propuesta).

**Sección Rankings**: `RankingsPanel` con `Tabs` cargando los 5 rankings de `rankings` (§7.9 propuesta).

**Sección Impacto**: lista ordenada por `impact_points` desc, formato "Esta categoría representa X puntos perdidos de NPS" (decisión §16 de `00_decisiones_tecnicas.md`).

**Sección "Acciones sugeridas"**: `ActionsPanel` con top 10 de `actions` (§7.10 propuesta).

**Sección "Voz de los pasivos"** (decisión §17 de `00_decisiones_tecnicas.md`): consume `GET /national/passive-analysis`. Dos columnas:
- "Pasivos cerca de detractor (NPS=7)" con `CauseBucket[]`.
- "Pasivos cerca de promotor (NPS=8)" con `CauseBucket[]`.

**Footer**: `InsightsList` con 5–8 insights de `insights` (§12.1 propuesta).

### 4. Comparación nacional (`/national/compare`, §8 de propuesta)

Header con 2 `MonthSelector` lado a lado: "Mes A" y "Mes B". Al cambiar cualquiera, dispara `GET /national/compare?month_a=&month_b=` → `MonthlyComparison`.

**Tabla principal** (§8.3 propuesta):

| Métrica | Mes A | Mes B | Cambio |
|---|---:|---:|---:|
| NPS | nps_a | nps_b | nps_change |
| Promotores | distribution_a.promoters_pct | distribution_b.promoters_pct | Δ |
| Pasivos | … | … | … |
| Detractores | … | … | … |
| Respuestas | … | … | … |

**Sección causas**: dos columnas side-by-side mostrando `causes_a` y `causes_b`. Indicadores visuales (flecha arriba/abajo) en buckets listados en `causes_increased` / `causes_decreased`.

**Sección fortalezas**: análogo con `strengths_a`, `strengths_b`, `strengths_increased`, `strengths_decreased`.

**Sucursales**: dos tablas pequeñas:
- "Más mejoraron" (`branches_improved`).
- "Más empeoraron" (`branches_worsened`).

**Insight narrativo**: card al final con texto generado del estilo "De [mes A] a [mes B], el NPS nacional [subió/bajó] N puntos. La mejora/deterioro se relaciona con…" (§8.3 propuesta).

### 5. Selector de sucursal (`/branches`, §9 propuesta)

Pantalla intermedia para el selector. `BranchSelector` (combobox) ocupa el centro de la página. Consume `GET /branches?q=` para autocompletar (1,291 items, virtualizado).

Atajos rápidos arriba del combobox: chips clicables con "Sucursales críticas" (carga `GET /national/critical-branches?limit=10` y muestra links directos).

Default state (sin selección): card grande con mensaje "Selecciona una sucursal para ver detalle granular".

Tras seleccionar, navega a `/branches/{branchId}`.

### 6. Vista sucursal YTD (`/branches/:branchId`, §10 de propuesta)

Consume `GET /branches/{branchId}/ytd` → `BranchYTD`. Si 404, mostrar pantalla "Sucursal no encontrada" con CTA "Volver al selector".

**Header**: `branch_id` grande + status `Badge "Crítica"` si la sucursal aparece en `GET /national/critical-branches`.

**Banner condicional**: si `nps.nps_target === null` → banner azul "Esta sucursal no tiene NPS objetivo configurado en la fuente interna" (§10.3 propuesta).

**Misma estructura que vista nacional** + drill-downs específicos de sucursal:

- Hero con `NPSCard`s (NPS actual, objetivo, brecha) + `SyntheticTargetsBanner` si hay target.
- `DistributionChart` + `TrendChart` (mensual de la sucursal).
- `CausesPanel` (de `causes`) + `StrengthsPanel` (de `strengths`).
- `ActionsPanel` (de `actions`, §13.2 propuesta).
- **`WordsCloud`** (§10.7 propuesta) con `Tabs`: General | Promotores | Detractores | Por mes. Cada tab dispara `GET /branches/{id}/words?group=&top_n=30`.
- **`RepresentativeComments`** (§10.8 propuesta): 2 cards por bucket desde `representatives` (`GET /branches/{id}/representatives?n_per_topic=2`).
- **`PersonnelTable`** (§10.9 propuesta): tabla con nombre, polaridad, conteo, ejemplo verbatim, fecha.
- `InsightsList` con insights de la sucursal (§12.2 propuesta).

### 7. Comparación sucursal (`/branches/:branchId/compare`, §11 de propuesta)

Análogo a la comparación nacional, filtrado por sucursal. Consume `GET /branches/{branchId}/compare?month_a=&month_b=` → `MonthlyComparison`.

**Sección extra** que la nacional no tiene: "Cambios en personal mencionado entre meses". Muestra delta de personal entre mes A y mes B (entradas que aparecieron solo en uno o cambiaron de polaridad).

Resto idéntico a pantalla 4 (tabla principal, causas A/B, fortalezas A/B, palabras frecuentes, comentarios representativos por mes).

### 8. Sección admin POC (`/admin/*`, §3 de propuesta)

Sidebar interna (sub-router) con items:

- **Gestión de usuarios** (`/admin/users`) → placeholder.
- **Cargas** (`/admin/files`) → consume `GET /admin/files`, tabla read-only con `filename | sha256 (truncado) | rows_inserted | uploaded_at`.
- **Validación de archivos** (`/admin/runs`) → consume `GET /admin/runs`, dos tablas read-only: `annotation_runs` y `classifier_runs`.
- **Configuración** (`/admin/config`) → placeholder.
- **Monitoreo** (`/admin/monitoring`) → placeholder.
- **Logs** (`/admin/logs`) → placeholder.

Los items placeholder muestran card grande "No implementado en MVP" con CTA "Volver a Vista CX". Todos los items son navegables visualmente para que se perciba la separación con "Vista CX" (decisión §3 propuesta).

---

## Tests requeridos

Framework: `vitest` + `@testing-library/react` + `jsdom`.

- **`useAuth`**: guarda token tras `login()`, lo recupera de `localStorage` al montar, `isAuthenticated()` devuelve `false` si `exp` ya pasó.
- **`AuthGuard`**: redirige a `/login` cuando no hay token; renderiza children cuando sí.
- **Cliente API**: añade `Authorization: Bearer <token>` en cada request; si la respuesta es 401, borra token y redirige a `/login`.
- **`NPSCard`**: con `gap = 5` muestra verde; con `gap = -5` muestra ámbar; con `gap = -15` muestra rojo.
- **`DistributionChart`**: renderiza exactamente 3 sectores con suma de porcentajes = 100.
- **`CausesPanel`**: ordena items descendente por `count` aunque la entrada venga desordenada.
- **`MonthSelector`**: se llena correctamente con `months_available` de `GET /validation`.
- **`BranchSelector`**: filtra por substring case-insensitive en `branch_id`.
- **MSW handlers**: cada handler responde con estructura válida que pasa por `zod` o por validación de tipos (smoke test contra los DTOs).
- **`NationalYTDPage`**: renderiza sin errores con fixtures sintéticas activadas; muestra todas las secciones (hero, dist, trend, causes, strengths, critical, rankings, impact, actions, passive, insights).
- **`BranchYTDPage`**: con sucursal sin target muestra el banner correspondiente; con target lo oculta.
- **Routing**: navegación entre páginas funciona, query params se propagan, `useBranch()` lee `branchId` desde URL.

---

## Definition of Done

- `npm run build` exitoso. Bundle gzipped < 1 MB (sin optimización extrema; suficiente para hackathon).
- `npm test` pasa todos los tests listados arriba.
- Todas las 7 pantallas son navegables visualmente sin errores en consola.
- Con `VITE_USE_MOCKS=true` (default en dev), la app es completamente recorrible sin backend.
- Con `VITE_USE_MOCKS=false` apunta a `VITE_API_URL` y funciona contra M4.
- Diseño coherente: misma paleta, mismas primitives shadcn en toda la app, sin inconsistencias visibles (no se introducen otras libs de UI).
- Mensaje "Objetivos NPS sintéticos para demo" visible en cabeceras con brecha.
- Mensaje "Esta sucursal no tiene NPS objetivo configurado" visible cuando aplica.
- Sidebar muestra distinción visual entre "Vista CX" y "Administración" (§3 propuesta).
- Items admin no implementados muestran "No implementado en MVP" con CTA.
- `Dockerfile` build exitoso, contenedor sirve `dist/` en puerto 80 con nginx.
- `README.md` del paquete escrito en español con: instalación, dev server, build, regeneración del cliente OpenAPI, variables de entorno.
- `package.json` con scripts: `dev`, `build`, `preview`, `test`, `gen:api` (que invoca `scripts/generate_openapi_client.sh`).
- Sin secretos en archivos commiteables (`.env.local` ignorado; `.env.example` con `VITE_API_URL=http://localhost:8000`, `VITE_USE_MOCKS=true`).

---

## Riesgos específicos del módulo

- **Design system inconsistente** si dos sub-sesiones tocan el frontend en paralelo. Mitigación: fijar `tailwind.config.ts` desde el inicio, usar **solo** primitives shadcn (prohibido MUI / Chakra / Ant / Mantine). Validar en review de DoD.
- **TanStack Query con stale data tras upload**: la vista nacional sigue mostrando datos viejos si no se invalida el cache. Mitigación: invalidar explícitamente `['national']`, `['branches']`, `['validation']` después de cada `POST /upload` exitoso.
- **Recharts con muchos puntos**: poco probable que sea problema (el `MonthlyTrend` agregado es de 16 puntos máximo). Sin acción inmediata.
- **`WordsCloud` con 30+ palabras** colapsa en pantallas chicas (mobile). Mitigación: empezar con tabla simple (siempre legible); migrar a word cloud (e.g. `react-tagcloud`) solo si sobra tiempo en el hackathon.
- **`BranchSelector` con 1,291 sucursales**: si el `Combobox` de shadcn no virtualiza por default, el primer render pinta 1,291 nodos y lagea. Mitigación: usar `react-window` con `FixedSizeList` envolviendo el dropdown.
- **OpenAPI export desincronizado con MSW**: cuando M4 publique `openapi.json`, los handlers MSW pueden no coincidir con el tipo real. Mitigación: tras regenerar `schema.d.ts`, correr `vitest` y arreglar tipos rotos antes de marcar DoD.
- **JWT con `exp` decodificado client-side**: si el token está malformado, `atob` falla. El `try/catch` en `isAuthenticated()` lo cubre, pero documentar como riesgo aceptado para MVP (decisión §18 de `00_decisiones_tecnicas.md`).
- **401 en medio de una página**: con varios `useQuery` en paralelo, el primero que reciba 401 hará `window.location.href = '/login'` y los demás quedarán huérfanos. Aceptable para MVP, no requiere lógica fina de cancelación.
- **MSW solo funciona en navegador, no en SSR**: no aplica porque Vite SPA es client-side. Documentado para evitar confusión si alguien intenta migrar a Next.js (descartado en decisión §2).
- **Polling de `/upload/{id}/status` puede saturar la API**: limitar a intervalo 2s y detenerse cuando `status === 'done' | 'error'`.
