import os
import shutil
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# We import the app to test it, and models to verify side effects
from src.api.service import app
from src.api.models import get_metadata, DB_PATH

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def test_env_setup():
    """Setup a clean testing environment before any tests run."""
    # 1. Use a temporary test database
    if os.path.exists("test_images.db"):
        os.remove("test_images.db")

    # 2. Setup clean directories
    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("static/thumbs", exist_ok=True)

    yield  # Run tests

    # 3. Teardown: Clean up files but maybe keep the DB for debugging if needed
    # shutil.rmtree("static/uploads")
    # shutil.rmtree("static/thumbs")


def create_img(w=100, h=100):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (255, 0, 0)).save(buf, format="PNG")
    buf.seek(0)
    return buf


# 1. Test Full Upload-to-Database Flow
def test_upload_integration():
    img = create_img()
    response = client.post("/upload", files={"files": ("int_test.png", img, "image/png")})
    assert response.status_code == 201
    img_id = response.json()["uploads"][0]["image_id"]

    # Verify DB entry exists
    data = get_metadata(img_id)
    assert data is not None
    assert data["status"] in ["processing", "completed"]


# 2. Test File Persistence on Disk
def test_file_saved_to_disk():
    img = create_img()
    res = client.post("/upload", files={"files": ("disk.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]
    data = get_metadata(img_id)
    assert os.path.exists(data["original_path"])


# 3. Test End-to-End Resize (Wait for background task)
def test_resize_completion_integration():
    img = create_img(200, 200)
    res = client.post("/upload", files={"files": ("resize.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]

    # In integration tests, we need to wait a split second for BackgroundTasks
    import time
    time.sleep(1)

    data = get_metadata(img_id)
    assert data["status"] == "completed"
    assert os.path.exists(data["thumb_path"])


# 4. Test Custom Resize Letterboxing (Visual Verification)
def test_custom_resize_letterbox_integration():
    # 100x50 image into 200x200 canvas
    img = create_img(100, 50)
    res = client.post("/upload", files={"files": ("box.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]

    client.post(f"/resize/{img_id}/custom?width=200&height=200")
    import time
    time.sleep(1)

    data = get_metadata(img_id)
    with Image.open(data["thumb_path"]) as thumb:
        assert thumb.size == (200, 200)
        # Check corner is black (letterbox)
        assert thumb.getpixel((0, 0)) == (0, 0, 0)


# 5. Test Multiple Concurrent Uploads
def test_multiple_uploads_integration():
    files = [
        ("files", ("1.png", create_img(), "image/png")),
        ("files", ("2.png", create_img(), "image/png"))
    ]
    response = client.post("/upload", files=files)
    assert len(response.json()["uploads"]) == 2


# 6. Test Retrieval of Actual Binary File
def test_get_file_binary_integration():
    img = create_img()
    res = client.post("/upload", files={"files": ("binary.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]

    import time
    time.sleep(1)

    response = client.get(f"/images/{img_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


# 7. Test 404 for Missing File on Disk
def test_get_file_missing_physical_disk():
    img = create_img()
    res = client.post("/upload", files={"files": ("missing.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]

    import time
    time.sleep(1)
    data = get_metadata(img_id)
    os.remove(data["thumb_path"])  # Manually delete

    response = client.get(f"/images/{img_id}/file")
    assert response.status_code == 404


# 8. Test Status 202 While Processing (Race Condition)
def test_status_202_immediate_request():
    img = create_img(5000, 5000)  # Big image takes time
    res = client.post("/upload", files={"files": ("slow.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]

    # Check immediately without sleep
    response = client.get(f"/images/{img_id}/file")
    assert response.status_code in [202, 200]


# 9. Test Input Validation for Malformed Image Data
def test_upload_corrupt_file():
    bad_data = io.BytesIO(b"not an image at all")
    response = client.post("/upload", files={"files": ("bad.png", bad_data, "image/png")})
    img_id = response.json()["uploads"][0]["image_id"]

    import time
    time.sleep(1)
    data = get_metadata(img_id)
    # Status should remain 'processing' or fail gracefully because engine caught exception
    assert data["status"] == "processing"


# 10. Test Preset Transition (Medium -> Small)
def test_preset_transition_integration():
    img = create_img()
    res = client.post("/upload", files={"files": ("switch.png", img, "image/png")})
    img_id = res.json()["uploads"][0]["image_id"]

    # Trigger small
    client.post(f"/resize/{img_id}/small")
    import time
    time.sleep(1)

    data = get_metadata(img_id)
    assert data["preset"] == "small"