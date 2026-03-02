from fastapi import FastAPI, UploadFile, File, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
import uuid
import os

# Internal imports
from src.resizer.engine import process_image
from src.api.models import init_db, save_metadata, get_metadata

app = FastAPI(title="Thumbnail Generation Service")

# Ensure directories exist for local storage
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/thumbs", exist_ok=True)


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/upload", status_code=201)
async def upload_images(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        preset: str = Query("medium", enum=["small", "medium", "large"])
):
    """Requirement: Upload one or more images."""
    results = []
    for file in files:
        if not file.content_type.startswith("image/"):
            continue  # Or raise HTTPException

        file_id = str(uuid.uuid4())
        extension = file.filename.split(".")[-1]
        original_path = f"static/uploads/{file_id}.{extension}"

        # Async save to disk
        with open(original_path, "wb") as buffer:
            buffer.write(await file.read())

        # Requirement: Concurrency (Processing in background)
        # In a real app, this would be Celery. Here, BackgroundTasks is perfect.
        background_tasks.add_task(process_image, file_id, original_path, preset)

        results.append({"image_id": file_id, "status": "processing"})

    return {"uploads": results}


@app.get("/images/{image_id}")
async def get_image_metadata(image_id: str):
    """Requirement: Retrieve metadata."""
    metadata = get_metadata(image_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Image not found")
    return metadata


@app.get("/images/{image_id}/file")
async def get_image_file(image_id: str, thumb: bool = True):
    """Requirement: Retrieval of generated files."""
    metadata = get_metadata(image_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Image not found")

    path = metadata["thumb_path"] if thumb else metadata["original_path"]
    return FileResponse(path)