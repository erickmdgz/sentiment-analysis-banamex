# web — SPA del reto Banamex CX

SPA en React 18 + Vite + TypeScript que consume la API HTTP de M4 y materializa
las 7 pantallas del Gerente Nacional CX (login, upload + validación, vista
nacional YTD, comparación nacional, selector de sucursal + vista sucursal YTD,
comparación de sucursal y sección Admin POC).

En la Etapa 1 del hackathon **no hay backend real**: la app trabaja contra
[MSW](https://mswjs.io/) con respuestas sintéticas determinísticas
(`src/mocks/handlers.ts`). Cuando M4 publique `openapi.json`, se regenera
`src/api/schema.d.ts` y se cambia el flag `VITE_USE_MOCKS=false`.

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | URL base del backend M4. |
| `VITE_USE_MOCKS` | `true` (dev) | Si está activo, la app intercepta el fetch con MSW y no consulta la API real. |

`.env.development` ya activa MSW en dev. Para apuntar al backend real:

```bash
VITE_USE_MOCKS=false npm run dev
```

## Comandos

```bash
# Instalar dependencias
npm install

# Dev server (puerto 5173, MSW activo por default)
npm run dev

# Build de producción a dist/
npm run build

# Vista previa de la build
npm run preview

# Tipado estricto
npm run typecheck

# Tests (vitest + jsdom + MSW)
npm test

# Regenerar tipos desde openapi.json (cuando M4 lo publique en Etapa 2)
npx openapi-typescript ../api/openapi.json --output src/api/schema.d.ts
```

## Estructura

```
src/
├── api/                 # cliente fetch tipado + queryClient + hooks TanStack Query
├── components/          # primitives shadcn (ui/) + componentes de dominio
├── hooks/               # useAuth, useBranch
├── lib/                 # cn, format, colors, seed
├── mocks/               # fixtures + handlers MSW + browser/server setup
├── pages/               # 7 pantallas + AdminPage
├── App.tsx, main.tsx, routes.tsx, index.css
tests/                   # vitest + testing-library
```

## Notas para M4 → M5 (Etapa 2)

- `src/api/schema.d.ts` está derivado **a mano** de los DTOs de `01_contratos §4`.
  Cuando M4 exporte `openapi.json`, regenerar con `openapi-typescript` y arreglar
  cualquier tipo divergente antes de marcar la integración como DoD.
- Los handlers MSW respetan los DTOs y la convención de errores
  (`{detail, code, hint?}`).
- El token JWT vive en `localStorage.banamex_token`. Cualquier 401 limpia el
  token y redirige a `/login`.
- Las fixtures son determinísticas: la misma sucursal devuelve siempre el mismo
  NPS, distribución y comentarios entre recargas (PRNG sembrado con hash del
  `branch_id`).

## Demo del hackathon

- Login simulado (cualquier usuario/contraseña funciona).
- Banner "Objetivos NPS sintéticos para demo" visible en cabeceras con brecha.
- Banner azul "Esta sucursal no tiene NPS objetivo configurado…" cuando aplica.
- Sidebar separa visualmente "Vista CX" de "Administración".
- Items admin no implementados muestran "No implementado en MVP" con CTA a Vista CX.
