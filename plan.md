# MAPORA implementation plan and design choices

## Repository context

The selected MAPORA checkout had no app source, no usable `.gitmodules` mapping, and only an unresolved gitlink. The original gitlink is left untouched. This implementation adds a React/TypeScript/Vite frontend at the repository root. No backend functionality is claimed.

## Product design

A premium charcoal/black/orange spatial-intelligence brand, architectural detail, restrained motion, responsive public story and consistent dark workspace. The revised hero reads “Every Space Has a Story. Map It Into Reality.” A four-stage Capture → Understand → Reconstruct → Explore interaction includes keyboard controls, annotations and reduced-motion support. The immersive demo pairs an illustrative floor plan with a 3D inset and uses a locally optimized, credited illustrative interior still.

## Implemented architecture

- React Router canonical routes with legacy `/app` redirect aliases and a static route manifest.
- Typed `src/services/api.ts` boundary controlled by `VITE_MAPORA_API_BASE`.
- In-memory auth, configured-workspace redirect, role-aware Admin guard and `admin`/`surveyor` role behavior.
- Shared project API hook that separates fixtures from live responses and surfaces loading/error/empty/retry states.
- Focused login, project/version-management, upload, processing, floor-plan, admin and lazy Three.js route components.
- Typed room/wall geometry; authenticated server exports; authorized remote model URL loading; optional admin job lists/filtering/retry.

## Honesty and safety decisions

No fake credentials, identity, project success, progress, geometry, analytics or persistence. Local edits are drafts. Sample SVG download is labelled. Deletion requires a typed-name confirmation. Backend can reject every proposed write; its errors remain visible. Admin data and job status are server-provided only. UI roles do not replace backend authorization. Tokens are not persisted to local storage. The stock interior is disclosed in `public/images/ASSET-CREDITS.md`; confirm license/attribution or replace before production.

## Validation targets

Run strict production TypeScript/Vite build and dependency audit; validate route JSON; directly exercise every route, search, auth redirect, upload validation, editor controls and sample/backend scene states; check browser console, reduced-motion behavior, responsive layouts, and public preview.

## Remaining backend choices

The exact API route shape, login/session security, roles, upload/retention limits, project/version mutation permissions, job/status taxonomy, floor-plan coordinates and measurement guarantees, model URL authorization/TTL, exports and admin analytics remain unconfirmed. Proposed contracts are in `docs/backend-integration.md` and require backend-owner confirmation.
