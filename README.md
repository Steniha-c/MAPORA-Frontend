# MAPORA

A responsive React + TypeScript frontend for exploring MAPORA, a video-to-spatial mapping product. The repository contains frontend source only; it has no mapping, authentication, persistence, or analytics backend.

## Run locally

Requires Node.js 22 or compatible.

```bash
npm install
npm run dev -- --host 0.0.0.0
npm run build
npm run preview -- --host 0.0.0.0
```

To connect an API, set `VITE_MAPORA_API_BASE` in the environment before starting Vite or building the app. See [`docs/backend-integration.md`](docs/backend-integration.md) for the proposed contracts. Do not place secret credentials in a `VITE_` variable: Vite values are bundled into the browser app.

## Homepage and visual assets

The public homepage follows the provided cinematic black-and-orange architecture reference: full-bleed hero, animated four-step workflow, spatial capability matrix, interactive sample 2D/3D preview tabs, technology band, CTA and responsive footer. Generated architecture visuals are concept illustrations only; floor-plan geometry, rooms, pathways and the 3D model are not claimed to be real scans or backend inference. Asset notes are in [`public/images/ASSET-CREDITS.md`](public/images/ASSET-CREDITS.md).

## Repository smoke tests

Run `npm test` to build the production bundle and verify the standalone output, route manifest, required docs, and packaged visual assets using Node’s built-in test runner. No test framework dependency is required.

## Demo and connected modes

- **Without `VITE_MAPORA_API_BASE`:** the workspace remains explorable with clearly labelled sample projects, sample SVG floor-plan geometry, and an interactive illustrative 3D scene. No upload, reconstruction, authentication, persistence, or analytics is simulated as successful. The sample SVG export is labelled as illustrative.
- **With an API base URL:** lists and details request live project data. Upload is sent as a multipart request; processing states are polled from the backend. Floor-plan geometry and the authorized 3D model URL are loaded from the backend. API errors, empty responses, pending state, and missing models remain visible rather than being replaced with sample data.

The app supports backend login roles `admin` and `surveyor`; administrator analytics are restricted to `admin`. A configured workspace redirects unauthenticated users to `/login`. The bearer token is held in memory only, so reloads require a new login. Production deployments should use the backend's approved secure session strategy and server-side authorization; role checks in the UI are not a substitute for server checks.

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Marketing homepage with interactive sample spatial showcase |
| `/login` | Backend-only sign-in with validation and API error states |
| `/dashboard` | Overview with live projects or labelled sample fixtures |
| `/projects` | Project search, status filter, open actions, and API loading/error/empty states |
| `/projects/new` | Video selection and backend upload |
| `/projects/:id` | Project detail, rename/delete confirmation, and backend version history/actions |
| `/projects/:id/upload` | Upload/re-upload a walkthrough for a project |
| `/projects/:id/processing` | Backend-polled progress, completion, failure, and retry |
| `/projects/:id/floor-plan` | Floor-plan viewer/editor, local draft labels, and applicable exports |
| `/projects/:id/3d` | Interactive sample scene or backend-provided GLTF/GLB scene |
| `/settings` | Workspace/API setup status and integration guidance |
| `/admin` | Admin-only backend analytics; unavailable values are never guessed |

Legacy `/app...` paths redirect to canonical routes.

## Architecture

- `src/services/api.ts` is the sole typed API boundary. It reports missing configuration, sends bearer tokens when available, and exposes server errors to the UI.
- `src/auth` provides in-memory auth state and role guards. No default password, credential, or fake session is embedded.
- `src/hooks/useProjects.ts` distinguishes sample mode from API mode. A failed live request does not silently fall back to sample rows.
- `src/pages` contains focused route components. The heavier Three.js scene is lazy-loaded.
- `public/manus-routes.json` registers canonical routes and redirects.

The route, API, geometry, authorization, and error contracts documented in `docs/backend-integration.md` are **frontend expectations only**. They do not imply that any server endpoints already exist.
