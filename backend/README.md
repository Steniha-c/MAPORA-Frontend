# MAPORA — AI Spatial Mapping Backend

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Pytest-29%2F29%20Passing-brightgreen?logo=pytest&logoColor=white)](https://docs.pytest.org/)

**MAPORA Backend** is an AI-powered indoor spatial mapping platform that transforms a continuous walkthrough video captured from a single monocular smartphone camera into structured 2D architectural CAD floor plans and interactive 3D GLB spatial models.

Built to integrate seamlessly with the existing [MAPORA-Frontend](https://github.com/Steniha-c/MAPORA-Frontend) React/TypeScript application.

---

## 1. System Architecture & Features

- **Authentication & Role-Based Access Control**:
  - Secure bcrypt password hashing.
  - JWT access tokens with short expiration.
  - Revocable refresh token rotation stored in PostgreSQL.
  - Role isolation between `admin` and `surveyor`. Surveyors access only their authorized projects.
  - Endpoint rate limiting via SlowAPI.
- **Project & Version Management**:
  - Full CRUD operations with search, pagination, and status tracking.
  - Automated version snapshotting on geometry edits with rollback capability.
  - Audit event logging for sensitive operations.
- **Video Upload API**:
  - Chunked streaming uploads outside web roots.
  - Strict validation of MIME types, magic bytes, and file size limits (up to 500 MB).
  - Storage backends: Local disk or S3/MinIO compatible object storage.
- **Asynchronous Background Processing Pipeline**:
  - Celery workers with Redis broker.
  - Observable states: `queued` → `validating` → `extracting_keyframes` → `estimating_geometry` → `generating_floor_plan` → `generating_3d_model` → `completed` (plus `failed` and `cancelled`).
  - Real database-backed polling API.
- **Modular AI & Computer Vision Reconstruction**:
  - **Stage A**: OpenCV decoding, focus metric (Laplacian variance), visual difference keyframe extraction.
  - **Stage B**: Feature-based visual odometry (ORB detector, Essential matrix decomposition, scale normalization).
  - **Stage C**: PyTorch Monocular Depth estimation adapter (MiDaS/DPT) with heuristic fallback.
  - **Stage D**: Semantic segmentation of walls, floors, ceilings, and openings.
  - **Stage E**: 3D back-projection into unified point clouds, voxel filtering, and floor normalization.
  - **Stage F**: 2D floor plan generation via gravity slice, Hough transform, and polygon fitting.
  - **Stage G**: Extruded 3D GLB model generation with interactive room node names.
- **Architectural Exporters**:
  - Vector SVG floor plans (`svgwrite`).
  - Professional PDF sheets with room schedules (`reportlab`).
  - AutoCAD DXF files with dedicated layers (`ezdxf`).
  - Binary 3D GLB scenes (`trimesh`).
- **Database-Backed Admin Analytics**:
  - Real metrics for projects, users, active jobs, failure rates, duration averages, and confidence scores.

---

## 2. Quickstart & Installation

### Option A: Local Python Environment (Windows / Linux / macOS)

#### 1. Clone repository
```bash
git clone https://github.com/Steniha-c/MAPORA-backend.git
cd MAPORA-backend
```

#### 2. Create virtual environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure environment
```bash
copy .env.example .env   # On Windows
cp .env.example .env     # On Linux/macOS
```

#### 5. Run Database Migrations
```bash
alembic upgrade head
```
*(Note: If PostgreSQL is not running locally, the backend automatically uses a local SQLite fallback database `mapora_dev.db` for instant development).*

#### 6. Start the API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation is immediately available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Option B: Docker Compose (Full Stack with PostgreSQL, Redis, MinIO)

```bash
docker compose up -d --build
```
This starts:
- `web`: FastAPI backend at [http://localhost:8000](http://localhost:8000)
- `worker`: Celery AI reconstruction worker
- `db`: PostgreSQL 16 on port 5432
- `redis`: Redis 7 on port 6379
- `minio`: S3 Storage on ports 9000 & 9001

---

## 3. Frontend Integration

In the [MAPORA-Frontend](https://github.com/Steniha-c/MAPORA-Frontend) repository:
1. Open `.env` and set:
   ```env
   VITE_MAPORA_API_BASE=http://localhost:8000
   ```
2. Start the frontend:
   ```bash
   npm run dev
   ```
3. Log in with the initial administrator account:
   - **Email**: `admin@mapora.io`
   - **Password**: `AdminMapora2026!`

For complete request/response contracts and details, see [docs/API_INTEGRATION_GUIDE.md](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-backend/docs/API_INTEGRATION_GUIDE.md).

---

## 4. Automated Testing

Run the full automated test suite (29 tests):
```bash
pytest tests/ -v
```

Test coverage includes:
- Authentication & JWT token revocation.
- Surveyor project isolation & admin privilege enforcement.
- Project CRUD, version snapshotting, and rollback.
- Video upload validation & MIME checks.
- Job state transitions & cancellation.
- Floor plan interactive editing & boundary schema validation.
- File export engines (SVG, PDF, DXF, GLB).
- End-to-end Computer Vision reconstruction pipeline.
- Frontend contract validation.

---

## 5. Status & Implementation Matrix

| Component | Working Functionality | Model-Dependent / External Binary | Future Scope |
|---|---|---|---|
| **Authentication & RBAC** | Fully operational (JWT, Bcrypt, Revocable refresh, Roles) | None | OAuth2 social login (Google/GitHub) |
| **Project CRUD & Versioning** | Fully operational with PostgreSQL/SQLite | None | Multi-branch version graphs |
| **Video Preprocessing (Stage A)** | Fully operational (OpenCV decode, Laplacian sharpness filter, Keyframes) | None | Hardware-accelerated NVDEC video decoding |
| **Visual Odometry (Stage B)** | Fully operational (ORB features, Essential matrix, camera trajectory) | COLMAP / ORB-SLAM3 adapter hook | Loop-closure bundle adjustment |
| **Depth Estimation (Stage C)** | Heuristic indoor geometric depth active out of the box | PyTorch MiDaS / DPT models (auto-loaded when weights cached) | Multi-view stereo neural radiance fields (NeRF) |
| **Semantics (Stage D)** | Perspective geometric and line-opening segmenter active | Deep semantic segmentation models | Fine-grained furniture classification |
| **Spatial Fusion (Stage E)** | Point cloud back-projection, voxel filtering, floor alignment | None | Dense mesh Poisson surface reconstruction |
| **2D Floor Plan (Stage F)** | Gravity slice, Hough wall extraction, room boundaries | None | Automatic door-swing angle detection |
| **3D Model Generation (Stage G)** | Extruded 3D GLB export with interactive room nodes | None | PBR textured materials |
| **Exports** | Vector SVG, Architectural PDF, AutoCAD DXF, and 3D GLB | None | IFC / BIM standard export |
| **Admin Analytics** | Real database-backed queries for projects, users, jobs, durations | None | Prometheus / Grafana metrics exporter |

---

## 6. Directory Structure

```text
MAPORA-backend/
├── app/
│   ├── main.py                   # FastAPI application gateway & lifespan
│   ├── core/                     # Configuration, security, rate limiting, logging
│   ├── db/                       # SQLAlchemy engine, session, Base
│   ├── models/                   # Database entities (User, Project, FloorPlan, etc.)
│   ├── schemas/                  # Pydantic v2 validation models
│   ├── api/v1/                   # REST API routes (Auth, Projects, Uploads, Jobs, etc.)
│   ├── services/                 # Business logic services
│   ├── storage/                  # Local and S3/MinIO storage providers
│   ├── reconstruction/           # Computer vision pipeline (Stages A - G)
│   ├── exports/                  # SVG, PDF, DXF, and GLB export engines
│   └── workers/                  # Celery worker configuration and tasks
├── alembic/                      # Database migration scripts
├── docs/                         # Integration, architecture, and model guides
├── tests/                        # 29 automated pytest test suites
├── Dockerfile                    # Container definition
├── docker-compose.yml            # Multi-container local stack
├── .env.example                  # Environment variable reference
└── requirements.txt              # Pinned Python dependencies
```

---

## 7. License

Licensed under the Apache License 2.0.
