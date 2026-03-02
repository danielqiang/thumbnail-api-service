import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.service import app

client = TestClient(app)


@patch("src.api.service.save_initial_upload")
@patch("src.api.service.process_image")
@patch("src.api.service.init_db")
class TestService:

    # 1. Test Successful Upload
    def test_upload_images_success(self, mock_init, mock_engine, mock_save):
        # We mock 'open' to avoid writing to disk
        with patch("builtins.open", MagicMock()):
            files = [("files", ("test.png", b"fake_data", "image/png"))]
            response = client.post("/upload", files=files)

            assert response.status_code == 201
            assert "uploads" in response.json()
            assert mock_save.called
            assert mock_engine.called

    # 2. Test Upload Filter (Ignore non-images)
    def test_upload_filter_non_images(self, mock_init, mock_engine, mock_save):
        files = [("files", ("test.txt", b"hello", "text/plain"))]
        response = client.post("/upload", files=files)

        assert response.status_code == 201
        assert len(response.json()["uploads"]) == 0
        assert not mock_save.called

    # 3. Test Resize Request Success
    @patch("src.api.service.get_metadata")
    def test_resize_request_success(self, mock_get, mock_init, mock_engine, mock_save):
        mock_get.return_value = {"original_path": "static/uploads/test.jpg"}

        response = client.post("/resize/valid-uuid/small")

        assert response.status_code == 200
        assert response.json()["message"] == "Task queued"
        # Verify background task was added with 'small'
        mock_engine.assert_called_once()

    # 4. Test Resize Request 404 (Missing ID)
    @patch("src.api.service.get_metadata")
    def test_resize_request_404(self, mock_get, mock_init, mock_engine, mock_save):
        mock_get.return_value = None
        response = client.post("/resize/missing-uuid/small")
        assert response.status_code == 404

    # 5. Test Custom Resize Validation (Missing width/height)
    @patch("src.api.service.get_metadata")
    def test_custom_resize_validation_error(
        self, mock_get, mock_init, mock_engine, mock_save
    ):
        mock_get.return_value = {"original_path": "path"}
        # Custom preset without width or height query params should fail with 400
        response = client.post("/resize/uuid/custom")
        assert response.status_code == 400

    # 6. Test Metadata Retrieval Success
    @patch("src.api.service.get_metadata")
    def test_get_info_success(self, mock_get, mock_init, mock_engine, mock_save):
        mock_get.return_value = {"id": "uuid", "status": "completed"}
        response = client.get("/images/uuid")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    # 7. Test File Retrieval (Processing Status 202)
    @patch("src.api.service.get_metadata")
    def test_get_file_still_processing(
        self, mock_get, mock_init, mock_engine, mock_save
    ):
        mock_get.return_value = {"status": "processing"}
        response = client.get("/images/uuid/file")
        assert response.status_code == 202
        assert "still being processed" in response.json()["detail"]

    # 8. Test File Retrieval (Missing from Disk 404)
    @patch("src.api.service.get_metadata")
    @patch("src.api.service.os.path.exists")
    def test_get_file_missing_on_disk(
        self, mock_exists, mock_get, mock_init, mock_engine, mock_save
    ):
        mock_get.return_value = {
            "status": "completed",
            "thumb_path": "path/to/thumb.png",
        }
        mock_exists.return_value = False
        response = client.get("/images/uuid/file")
        assert response.status_code == 404
        assert "missing from storage" in response.json()["detail"]

    # 9. Test Query Parameter Validation (gt=0)
    def test_resize_invalid_dimensions(self, mock_init, mock_engine, mock_save):
        # width = 0 should trigger FastAPI validation error (422)
        response = client.post("/resize/uuid/custom?width=0")
        assert response.status_code == 422

    # 10. Test Invalid Preset Enum
    def test_invalid_preset_enum(self, mock_init, mock_engine, mock_save):
        # 'huge' is not in ResizePreset enum
        response = client.post("/resize/uuid/huge")
        assert response.status_code == 422
