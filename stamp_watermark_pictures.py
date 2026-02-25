import os
from PIL import Image, ImageDraw, ImageFont

INPUT_DIRECTORY = "stamp_photos\\pre_stamp"
OUTPUT_DIRECTORY = "stamp_photos\\post_stamp"

# Your watermark text (e.g. your name, brand, "© 2026")
WATERMARK_TEXT = "Ценалитика"

def stamp_watermark_on_images(directory, output_dir, watermark_text=WATERMARK_TEXT, opacity=0.08):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            path = os.path.join(directory, filename)
            img = Image.open(path).convert("RGBA")

            txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            width, height = img.size
            font_size = int(height * 0.1)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            # Center on main image
            x = (width - text_w) // 2
            y = (height - text_h) // 2
            alpha = int(255 * opacity)
            draw.text((x, y), watermark_text, font=font, fill=(0, 0, 0, alpha))

            # Rotate the layer (assign result; rotate returns a new image)
            txt_layer = txt_layer.rotate(20, expand=True)
            rot_w, rot_h = txt_layer.size

            # Center the rotated layer on the main image
            x_pos = (width - rot_w) // 2
            y_pos = (height - rot_h) // 2
            img.paste(txt_layer, (x_pos, y_pos), txt_layer)

            img.convert("RGB").save(os.path.join(output_dir, filename))

stamp_watermark_on_images(INPUT_DIRECTORY, OUTPUT_DIRECTORY)