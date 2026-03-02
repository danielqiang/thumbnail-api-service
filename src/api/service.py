import uuid
import shutil
import os
from enum import Enum
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.models import init_db, save_initial_upload, get_metadata
from src.resizer.engine import process_image

app = FastAPI(title="Pro Thumbnail API")

# Initialize directories and DB
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/thumbs", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ResizePreset(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"
    custom = "custom"


@app.on_event("startup")
def startup():
    init_db()


@app.post("/upload", status_code=201)
async def upload_images(
    background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)
):
    results = []
    for file in files:
        if not file.content_type.startswith("image/"):
            continue

        file_id = str(uuid.uuid4())
        ext = file.filename.split(".")[-1] or "jpg"
        original_path = f"static/uploads/{file_id}.{ext}"

        with open(original_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        save_initial_upload(file_id, original_path)

        # Auto-resize to medium as a default background task
        background_tasks.add_task(process_image, file_id, original_path, "medium")
        results.append({"image_id": file_id, "filename": file.filename})

    return {"uploads": results}


@app.post("/resize/{image_id}/{preset}")
async def resize_request(
    image_id: str,
    preset: ResizePreset,
    background_tasks: BackgroundTasks,
    width: Optional[int] = Query(None, gt=0),
    height: Optional[int] = Query(None, gt=0),
):
    data = get_metadata(image_id)
    if not data:
        raise HTTPException(404, "Original image not found")

    if preset == ResizePreset.custom and not (width or height):
        raise HTTPException(400, "Custom preset requires width and height")

    background_tasks.add_task(
        process_image, image_id, data["original_path"], preset.value, width, height
    )
    return {"message": "Task queued", "image_id": image_id}


@app.get("/images/{image_id}")
async def get_info(image_id: str):
    data = get_metadata(image_id)
    if not data:
        raise HTTPException(404, "Not found")
    return data


@app.get("/images/{image_id}/file")
async def get_file(image_id: str):
    data = get_metadata(image_id)

    if not data:
        raise HTTPException(status_code=404, detail="Image record not found")

    # CRITICAL: Prevent streaming a half-written file
    if data["status"] != "completed":
        raise HTTPException(
            status_code=202,
            detail="Image is still being processed. Please try again in a few seconds.",
        )

    # Verify the file actually exists on the disk
    if not os.path.exists(data["thumb_path"]):
        raise HTTPException(status_code=404, detail="File missing from storage")

    return FileResponse(data["thumb_path"])


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
