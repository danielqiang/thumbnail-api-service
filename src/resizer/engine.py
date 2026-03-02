from PIL import Image
from src.api.models import save_metadata

PRESETS = {
    "small": (128, 128),
    "medium": (512, 512),
    "large": (1024, 1024)
}


def process_image(image_id: str, original_path: str, preset: str):
    target_size = PRESETS.get(preset, PRESETS["medium"])

    with Image.open(original_path) as img:
        # Requirement: Resize while preserving aspect ratio
        img.thumbnail(target_size)

        thumb_path = f"static/thumbs/{image_id}.png"
        img.save(thumb_path)
        width, height = img.size

        # Save results to DB so GET /images/{id} can find it
        save_metadata(image_id, original_path, thumb_path, width, height)