# MAPORA frontend ↔ backend integration contract

## Current state

The selected MAPORA repository had no app source, `.gitmodules` mapping, or backend. This frontend therefore defines a clear API boundary but cannot verify server endpoints. The routes below are proposed integration contracts implemented by the frontend; they are not claims that those routes exist. Configure `VITE_MAPORA_API_BASE` only after the backend owner confirms the base URL, route shapes, authentication model, validation limits, and CORS behavior.

Without an API base, public marketing pages and clearly labelled sample views work locally. Login rejects without a configured API; video selection never claims an upload occurred; status is not simulated; the floor-plan SVG export includes an illustrative-sample disclaimer; and the 3D model is visibly marked as demo geometry. Once an API base is configured, missing live project/model/geometry data is shown as unavailable instead of being replaced by sample records.

## Proposed API

All JSON endpoints use `application/json`, except multipart upload. Successful deletion/restore may return `204 No Content`. Errors should return a useful JSON `message` or `error`; the client displays the returned explanation. Use HTTPS, explicit allowed origins, and server-side authorization for every protected operation.

| Method | Path | Frontend behavior / expected response |
| --- | --- | --- |
| `POST` | `/auth/login` | JSON `{email,password}` → `{accessToken,user:{id,email,role}}`; role is `admin` or `surveyor`. No credential is seeded. |
| `GET` | `/projects` | Array of `MapProject` records. |
| `POST` | `/projects` | Multipart field `video` → `{id,status}`; the client routes to processing only after an accepted response. Define upload size/type limits and return them from the server before release. |
| `GET` | `/projects/:id` | One `MapProject`. |
| `PATCH` | `/projects/:id` | JSON `{name}` → updated `MapProject`; UI surfaces permission/validation failures. |
| `DELETE` | `/projects/:id` | Authenticated delete; UI requires the user to type the exact project name before request. The backend remains authoritative. |
| `GET` | `/projects/:id/versions` | Array of `ProjectVersion` records. Empty history is distinct from failure. |
| `POST` | `/projects/:id/versions` | Create a version if the backend supports it → `ProjectVersion`. |
| `POST` | `/projects/:id/versions/:versionId/restore` | Restore a backend version if permitted; refresh project/history after success. |
| `GET` | `/projects/:id/status` | `ProcessingStatus`, polled by the client. `status` may be `queued`, `processing`, `completed`, `failed`, or `unknown`; optional `progress` must be numeric 0–100. |
| `POST` | `/projects/:id/retry` | Request a failed-job retry; the server returns current `ProcessingStatus`. |
| `GET` | `/projects/:id/floor-plan` | `FloorPlanModel` described below. Missing geometry is an error/empty state, not sample fallback. |
| `GET` | `/projects/:id/scene` | `{geometryUrl}` with a short-lived authorized GLTF/GLB URL. The model host must permit the frontend origin for fetch/CORS. A missing/expired/unsupported URL produces a visible error/retry state. |
| `GET` | `/projects/:id/export?format=svg\|dxf\|pdf\|obj\|gltf\|glb` | Authenticated downloadable blob. Server returns an appropriate content type and disposition; the UI exposes only confirmed project geometry and shows failures. |
| `GET` | `/admin/analytics` | Admin-only `AdminAnalytics`; metrics and update time are supplied by the server. Optional `recentJobs` records power admin search/status filters and failed-job retry. No client-derived or invented usage totals. |

### Type expectations

`MapProject`: `id`, `name`, `location`, `createdAt`, `status` (`Ready`, `Processing`, `Needs attention`), `rooms`, `duration`, and `color`; `updatedAt` and `versionCount` are optional. Align status/date conventions with the backend before release.

`ProcessingStatus`: `projectId`, `stage`, `status`, optional numeric `progress`, `message`, and `updatedAt`. The client never synthesizes a successful completion.

`FloorPlanModel`:

```json
{
  "coordinateSystem": "backend-defined local coordinate frame",
  "units": "m",
  "measurementsAvailable": true,
  "rooms": [
    { "id": "room-1", "name": "Living room", "bounds": { "x": 0, "y": 0, "width": 4.2, "height": 3.1 }, "areaSquareMeters": 13.02 }
  ],
  "walls": [
    { "id": "wall-1", "start": { "x": 0, "y": 0 }, "end": { "x": 4.2, "y": 0 }, "kind": "wall" }
  ]
}
```

Rooms and walls share one coordinate system. `areaSquareMeters` should be omitted unless measured/validated; set `measurementsAvailable` false if dimensions are not trustworthy. The editor normalizes returned coordinates for display but edits room labels only in local draft state; geometry edits are not written to the server. `wall.kind` is `wall` or `door`.

`AdminAnalytics`: `projectCount`, `userCount`, `jobsRunning`, `jobsFailed`, `updatedAt`; optional `jobsCompleted`, `averageProcessingSeconds`, `reconstructionsCompleted`, `roomsDetected`, `averageGeometryConfidence` (0–1), and `recentJobs`. Each `AdminJob` should include `id`, `projectId`, `projectName`, `stage`, `status`, `updatedAt`, and optional `durationSeconds` and `message`. Failed-job retry requests use the job project’s retry endpoint; server permission checks are authoritative. Ensure all aggregates are scoped and authorized server-side.

## Auth and privacy

- Login response is held in React memory; it is not placed in local storage or embedded into the bundle. Page reload requires login again.
- A connected workspace redirects to `/login` without a session; `/admin` additionally requires the `admin` role. The server must independently enforce the same permissions.
- Use secure cookies/refresh-token architecture only after the auth owner selects and reviews it. Do not expose passwords, service keys, or long-lived secrets to `VITE_` variables.
- Configure upload limits, MIME/container validation, retention, signed model URL TTL, authorization, and export permissions with the service owner.

## Integration checklist

1. Backend owner confirms route paths, field names, response types, status taxonomy, roles, and upload/retention limits.
2. Add integration tests or a nonproduction API contract environment; verify login, denied roles, upload errors, polling, retry, geometry, exports, and delete confirmation.
3. Configure `VITE_MAPORA_API_BASE` in the deployment environment and CORS for the frontend origin.
4. Verify sample records are not present in live API failures and that metrics/models are only displayed after server response.
5. Define secure token/session handling, expiry, logout, CSRF strategy where relevant, and role enforcement server-side.
