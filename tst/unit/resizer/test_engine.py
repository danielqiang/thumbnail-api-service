import pytest
from unittest.mock import patch, MagicMock
from src.resizer.engine import process_image


@patch("src.resizer.engine.Image")
@patch("src.resizer.engine.update_resize_status")
@patch("src.resizer.engine.os.makedirs")
class TestEngine:

    def setup_method(self):
        # This ensures that in every test, the LANCZOS mock returns 1
        # so it matches our integer assertions.
        pass

    def test_landscape_scaling(self, mock_mkdir, mock_update, mock_PIL):
        mock_PIL.Resampling.LANCZOS = 1
        mock_img = MagicMock(width=1000, height=500)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        process_image("id1", "fake.png", "small")
        mock_img.resize.assert_called_with((128, 64), 1)

    def test_portrait_scaling(self, mock_mkdir, mock_update, mock_PIL):
        mock_PIL.Resampling.LANCZOS = 1
        mock_img = MagicMock(width=500, height=1000)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        process_image("id2", "fake.png", "small")
        mock_img.resize.assert_called_with((64, 128), 1)

    def test_upscale_small_image(self, mock_mkdir, mock_update, mock_PIL):
        mock_PIL.Resampling.LANCZOS = 1
        mock_img = MagicMock(width=10, height=10)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        process_image("id3", "fake.png", "medium")
        mock_img.resize.assert_called_with((512, 512), 1)

    def test_centering_offset(self, mock_mkdir, mock_update, mock_PIL):
        # FIX: We must mock the RETURN of .resize() so its .width/height work
        mock_orig = MagicMock(width=100, height=50)
        mock_PIL.open.return_value.__enter__.return_value = mock_orig

        mock_resized = MagicMock(width=128, height=64)
        mock_orig.resize.return_value = mock_resized

        mock_canvas = MagicMock()
        mock_PIL.new.return_value = mock_canvas

        process_image("id4", "fake.png", "small")

        # (128 - 64) // 2 = 32
        mock_canvas.paste.assert_called()
        offset = mock_canvas.paste.call_args[0][1]
        assert offset == (0, 32)

    def test_canvas_initialization(self, mock_mkdir, mock_update, mock_PIL):
        mock_img = MagicMock(width=100, height=100)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        process_image("id5", "fake.png", "large")
        mock_PIL.new.assert_called_with("RGB", (1024, 1024), (0, 0, 0))

    def test_custom_dimensions_math(self, mock_mkdir, mock_update, mock_PIL):
        mock_PIL.Resampling.LANCZOS = 1
        mock_img = MagicMock(width=100, height=100)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        # 100x100 into 300x600 -> factor is 3. New size 300x300.
        process_image("id6", "fake.png", "custom", custom_w=300, custom_h=600)
        mock_img.resize.assert_called_with((300, 300), 1)

    def test_db_update_params(self, mock_mkdir, mock_update, mock_PIL):
        mock_img = MagicMock(width=100, height=100)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        process_image("id7", "fake.png", "small")
        # Ensure update_resize_status is called with the target box size, not the inner image size
        mock_update.assert_called_once_with("id7", "static/thumbs/id7_small.png", 128, 128, "small")

    def test_mkdir_called(self, mock_mkdir, mock_update, mock_PIL):
        mock_img = MagicMock(width=100, height=100)
        mock_PIL.open.return_value.__enter__.return_value = mock_img

        process_image("id8", "fake.png", "small")
        mock_mkdir.assert_called_with("static/thumbs", exist_ok=True)

    def test_exception_handling(self, mock_mkdir, mock_update, mock_PIL):
        # Force an error on open
        mock_PIL.open.side_effect = Exception("Pillow Crash")

        # Should catch and not raise
        process_image("id9", "fake.png", "small")
        assert not mock_update.called

    def test_save_is_png(self, mock_mkdir, mock_update, mock_PIL):
        mock_img = MagicMock(width=100, height=100)
        mock_PIL.open.return_value.__enter__.return_value = mock_img
        mock_canvas = MagicMock()
        mock_PIL.new.return_value = mock_canvas

        process_image("id10", "fake.png", "small")
        mock_canvas.save.assert_called_with("static/thumbs/id10_small.png", "PNG")