# MAPORA frontend implementation outcomes

## Product experience — complete
- [x] Create a premium public MAPORA landing page with the exact follow-up hero “Every Space Has a Story. / Map It Into Reality.”, supporting copy, primary “Start Mapping” and secondary “Explore the Experience” actions, orange word emphasis, architectural pipeline, four-step process, features, immersive showcase and footer.
- [x] Add an interactive four-stage Capture → Understand → Reconstruct → Explore story with tab controls, playback, keyboard operation, reduced-motion support, annotations and sample disclaimers.
- [x] Show the immersive example as paired illustrative 2D floor plan and 3D spatial preview, supported by a sourced and optimized illustrative interior frame. The image source and production licensing caveat are documented in `public/images/ASSET-CREDITS.md`.
- [x] Include keyframes, pose estimation, monocular depth, wall/door/room semantics, 2D maps, 3D maps, pathway visualization, editing and exports as product capabilities; copy clearly distinguishes planned/connected capabilities from features active in this frontend.
- [x] Add responsive dark workspace navigation for Overview, New Mapping, My Projects, Floor Plans, 3D Viewer, Settings and role-aware Admin. Configured workspaces redirect unauthenticated users to sign-in; the offline demo workspace remains explorable.

## Identity and access — complete, backend-dependent
- [x] Implement sign-in validation, password visibility, loading/error states and API-only authentication success; no seeded credentials or fake sign-in.
- [x] Hold backend sessions in memory only, protect configured workspaces, guard Admin by `admin`, and show Admin/Surveyor role-aware behavior. Server-side permission checks remain required.
- [x] Add functional sign-in, sign-out, settings/help and global project-search navigation.

## Projects and processing — complete, backend-dependent
- [x] Use live API records when configured; show distinct loading/error/retry/empty states and never substitute sample fixtures after a live API failure. Search, status filtering, opening projects and project details are wired.
- [x] Add project rename, version list/create/restore and typed-name project-delete confirmation. Mutations appear only with an authenticated API session; errors/permission denials stay visible.
- [x] Add drag-and-drop/browse, video-type validation, file metadata and local preview, replace/remove, keyboard support, backend-limit disclosure and upload errors. Real upload occurs only through explicit submission to a configured API.
- [x] Poll backend processing status; display backend-provided stages/progress only; show unknown/loading/error/completed/failed and request retry only through the backend.

## Spatial editor and viewers — complete, backend-dependent
- [x] Load typed backend floor-plan room bounds, walls/doors, units and validated dimensions when returned; never substitute sample geometry on configured-API error.
- [x] Add keyboard-accessible room/wall selection, local label draft, undo/redo, pan/zoom/fit, grid/labels/measurement controls, discard/apply-local-draft states and explicit non-persistence copy. Geometry edits are not saved.
- [x] Add labelled client-side SVG download for illustrative sample geometry; request PDF/DXF/OBJ/GLTF/GLB from authenticated backend only for live geometry.
- [x] Load an authorized backend GLTF/GLB model URL where supplied; show loading/error/retry states. Offline mode has interactive, explicitly illustrative geometry and room selection; backend model selection uses semantic object labels when provided.

## Admin, quality and remaining integration
- [x] Add admin-only API analytics for projects, users, running/failed jobs and average processing duration; provide job search/status filters and retry actions backed by returned job IDs/processing API. No mock metrics are shown.
- [x] Add route manifest, run instructions, proposed endpoint/types/auth contract, privacy notes, and integration checklist. Backend contracts and server capabilities remain unverified; see `docs/backend-integration.md`.
- [x] Strict TypeScript/Vite production build passes; dependency audit reports zero vulnerabilities. Three.js is lazy-loaded as a separate chunk; Vite warns it is >500 kB minified.

The API, authentication/session strategy, upload policy, persistence, versioning/mutations, processing job service, generated geometry/model assets, export formats and analytics still require backend confirmation. The original unresolved repository gitlink remains untouched.
