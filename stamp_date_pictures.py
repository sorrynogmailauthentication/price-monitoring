import os
from PIL import Image, ImageDraw, ImageFont
import re

INPUT_DIRECTORY = "stamp_photos\pre_stamp"
OUTPUT_DIRECTORY = "stamp_photos\post_stamp"

def stamp_date_on_images(directory, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            path = os.path.join(directory, filename)
            img = Image.open(path)

            date_match = re.search(r'.*(\d{4}-\d{2}-\d{2})', filename)
            date_str = date_match.group(1) if date_match else "Unknown Date"
            
            # Prepare to draw
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            # Adjust font size based on image height (roughly 5% of height)
            font_size = int(height * 0.1)
            try:
                # Use a standard system font
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

            # Position text in bottom-right corner
            margin = 20
            # Use textbbox to get dimensions in newer Pillow versions
            bbox = draw.textbbox((0, 0), date_str, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = width - text_w - margin
            y = height - text_h - margin

            # Draw white text with a black shadow for readability
            draw.text((x+2, y+2), date_str, font=font, fill="black")
            draw.text((x, y), date_str, font=font, fill="red")

            img.save(os.path.join(output_dir, filename))
            print(f"Processed: {filename} ({date_str})")

# Usage
stamp_date_on_images(INPUT_DIRECTORY, OUTPUT_DIRECTORY)