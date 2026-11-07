"""Background processing tasks for spatial reconstruction."""

from datetime import datetime, timezone
import os
import tempfile
import time
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.job import ReconstructionJob
from app.models.project import Project
from app.models.upload import VideoUpload
from app.models.geometry import FloorPlan, Room, Wall, Model3D
from app.storage.provider import get_storage
from app.reconstruction.pipeline import SpatialReconstructionPipeline


def _format_duration(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def process_reconstruction_task(self, job_id: str):
    """
    Celery task orchestrating the end-to-end AI spatial reconstruction pipeline.
    Ensures accurate DB state transitions and real progress reporting.
    """
    db = SessionLocal()
    temp_video_file = None

    try:
        job = db.scalar(select(ReconstructionJob).where(ReconstructionJob.id == job_id))
        if not job:
            logger.error(f"Reconstruction job {job_id} not found in database.")
            return

        if job.status == "cancelled":
            logger.info(f"Reconstruction job {job_id} was cancelled before worker execution.")
            return

        project = db.scalar(select(Project).where(Project.id == job.project_id))
        upload = db.scalar(select(VideoUpload).where(VideoUpload.id == job.upload_id))

        if not project or not upload:
            job.status = "failed"
            job.error_message = "Associated project or video upload record was not found."
            db.commit()
            return

        # Start job
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        project.status = "Processing"
        db.commit()

        storage = get_storage()
        video_local_path = storage.get_file_path(upload.storage_key)

        if not video_local_path or not os.path.exists(video_local_path):
            # Stream from storage to temporary local file
            temp_dir = tempfile.gettempdir()
            temp_video_file = os.path.join(temp_dir, f"mapora_temp_{job.id}.mp4")
            with open(temp_video_file, "wb") as f_out:
                with storage.open(upload.storage_key) as f_in:
                    while True:
                        chunk = f_in.read(1024 * 1024)
                        if not chunk:
                            break
                        f_out.write(chunk)
            video_local_path = temp_video_file

        def on_progress(stage: str, progress: float, message: str):
            """Real-time progress callback updating DB for polling frontend."""
            job.stage = stage
            job.progress = progress
            job.message = message
            job.updated_at = datetime.now(timezone.utc)
            db.commit()

        # Run Modular Spatial Reconstruction
        pipeline = SpatialReconstructionPipeline()
        output = pipeline.run(video_local_path, progress_cb=on_progress)

        # 1. Update VideoUpload metadata
        upload.duration_seconds = output.video_info.duration_seconds
        upload.fps = output.video_info.fps
        upload.width = output.video_info.width
        upload.height = output.video_info.height
        upload.frame_count = output.video_info.total_frames
        upload.status = "processed"

        # 2. Deactivate previous floor plans and save new generated floor plan
        for old_plan in project.floor_plans:
            old_plan.is_active = False

        new_plan = FloorPlan(
            project_id=project.id,
            coordinate_system=output.floor_plan.coordinate_system,
            units=output.floor_plan.units,
            measurements_available=output.floor_plan.measurements_available,
            quality_confidence=output.floor_plan.quality_confidence,
            is_active=True,
        )
        db.add(new_plan)
        db.flush()

        for r_dict in output.floor_plan.rooms:
            b = r_dict.get("bounds", {})
            room = Room(
                floor_plan_id=new_plan.id,
                name=r_dict.get("name", "Room"),
                bounds_x=b.get("x", 0.0),
                bounds_y=b.get("y", 0.0),
                bounds_width=b.get("width", 1.0),
                bounds_height=b.get("height", 1.0),
                area_sqm=r_dict.get("areaSquareMeters"),
                confidence=output.floor_plan.quality_confidence,
            )
            db.add(room)

        for w_dict in output.floor_plan.walls:
            s = w_dict.get("start", {})
            e = w_dict.get("end", {})
            wall = Wall(
                floor_plan_id=new_plan.id,
                start_x=s.get("x", 0.0),
                start_y=s.get("y", 0.0),
                end_x=e.get("x", 1.0),
                end_y=e.get("y", 1.0),
                kind=w_dict.get("kind", "wall"),
                confidence=output.floor_plan.quality_confidence,
            )
            db.add(wall)

        # 3. Store 3D GLB Model
        model_storage_key = f"models/{project.id}/scene_{job.id}.glb"
        import io
        glb_io = io.BytesIO(output.model_3d.glb_bytes)
        storage.save(glb_io, model_storage_key, content_type="model/gltf-binary")

        model_record = Model3D(
            project_id=project.id,
            format="glb",
            storage_key=model_storage_key,
            file_size_bytes=len(output.model_3d.glb_bytes),
            vertex_count=output.model_3d.vertex_count,
            face_count=output.model_3d.face_count,
            metadata_json={"roomNames": output.model_3d.room_names},
        )
        db.add(model_record)

        # 4. Finalize Project and Job Status
        project.rooms_count = len(output.floor_plan.rooms)
        project.duration = _format_duration(output.video_info.duration_seconds)
        project.status = "Ready"

        job.status = "completed"
        job.stage = "completed"
        job.progress = 100.0
        job.message = "Reconstruction completed successfully."
        job.completed_at = datetime.now(timezone.utc)
        job.duration_seconds = output.duration_seconds

        db.commit()
        logger.info(f"Successfully finished reconstruction job {job.id} for project {project.name}")

    except Exception as e:
        logger.exception(f"Error during reconstruction job {job_id}: {e}")
        try:
            job = db.scalar(select(ReconstructionJob).where(ReconstructionJob.id == job_id))
            if job:
                job.status = "failed"
                job.error_message = f"Processing error: {str(e)}"
                job.completed_at = datetime.now(timezone.utc)
            project = db.scalar(select(Project).where(Project.id == job.project_id))
            if project:
                project.status = "Needs attention"
            db.commit()
        except Exception:
            pass
    finally:
        if temp_video_file and os.path.exists(temp_video_file):
            try:
                os.remove(temp_video_file)
            except Exception:
                pass
        db.close()
