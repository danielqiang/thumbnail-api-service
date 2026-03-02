import os
import traceback
from PIL import Image
from src.api.models import update_resize_status

PRESETS = {
    "small": (128, 128),
    "medium": (512, 512),
    "large": (1024, 1024)
}


def process_image(image_id, original_path, preset, custom_w=None, custom_h=None):
    try:
        # 1. Determine target box
        presets = {"small": (128, 128), "medium": (512, 512), "large": (1024, 1024)}
        target_w, target_h = presets.get(preset, (custom_w or 512, custom_h or 512))

        with Image.open(original_path) as img:
            # 2. Calculate Scaling Factor
            # We want the image to be as big as possible within the target box
            ratio_w = target_w / img.width
            ratio_h = target_h / img.height
            scaling_factor = min(ratio_w, ratio_h)

            # 3. Calculate new dimensions (preserving aspect ratio)
            new_size = (int(img.width * scaling_factor), int(img.height * scaling_factor))

            # 4. Resize (Using .resize instead of .thumbnail to FORCE scaling up)
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 5. Create the Black Canvas
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))

            # 6. Center the resized image on the canvas
            offset = (
                (target_w - resized_img.width) // 2,
                (target_h - resized_img.height) // 2
            )
            canvas.paste(resized_img, offset)

            # 7. Save and update DB
            thumb_path = f"static/thumbs/{image_id}_{preset}.png"
            os.makedirs("static/thumbs", exist_ok=True)
            canvas.save(thumb_path, "PNG")

            update_resize_status(image_id, thumb_path, target_w, target_h, preset)

        print(f"SUCCESS: {image_id} scaled to {new_size} on {target_w}x{target_h} canvas.")

    except Exception as e:
        print(f"Error in Processor: {e}")