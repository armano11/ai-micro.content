from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.utils.file_utils import get_project_file_path, get_project_dir
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ThumbnailService:
    @staticmethod
    def generate_thumbnail(project_id: str, title: str, image_paths: list[Path]) -> Path:
        """
        Generates a clickable, high-contrast YouTube Shorts / Reels style thumbnail.
        Selects the most dramatic scene image (defaults to scene 5 or scene 1),
        overlays high-contrast title text, adds a dark vignette for readability,
        and adds a professional 'Play' button overlay.
        """
        logger.info(f"Generating thumbnail for project {project_id}...")
        
        # 1. Select the most dramatic image (Scene 5 / Cliffhanger is usually best; fallback to Scene 1)
        selected_img_path = None
        if len(image_paths) >= 5:
            selected_img_path = image_paths[4] # Scene 5
        elif len(image_paths) >= 1:
            selected_img_path = image_paths[0] # Scene 1
            
        if not selected_img_path or not selected_img_path.exists():
            # If no images, create a blank dark card
            logger.warning("No scene images found. Generating a text-only thumbnail.")
            width, height = 1024, 1792
            img = Image.new("RGB", (width, height), "#0a0a16")
        else:
            img = Image.open(selected_img_path).copy()
            
        width, height = img.size
        draw = ImageDraw.Draw(img, "RGBA")
        
        # 2. Add a dark vignette overlay at the bottom and top to ensure text readability
        # Top gradient (fade from black to transparent)
        for y in range(400):
            alpha = int(220 * (1 - y / 400))
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
            
        # Bottom gradient (fade from transparent to black)
        for y in range(height - 500, height):
            progress = (y - (height - 500)) / 500
            alpha = int(220 * progress)
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
            
        # 3. Draw a glowing "Play" button in the center (makes it look highly clickable)
        play_size = 180
        center_x, center_y = width // 2, height // 2
        
        # Draw translucent outer glow circle
        draw.ellipse(
            [(center_x - play_size//2, center_y - play_size//2), 
             (center_x + play_size//2, center_y + play_size//2)], 
            fill=(255, 0, 0, 80),
            outline=(255, 255, 255, 120),
            width=5
        )
        
        # Draw inner play triangle
        tri_size = 45
        draw.polygon(
            [(center_x - tri_size//2, center_y - tri_size), 
             (center_x - tri_size//2, center_y + tri_size), 
             (center_x + tri_size, center_y)], 
            fill=(255, 255, 255, 240)
        )
        
        # 4. Draw high-contrast Title Text (Upper third or bottom)
        # Font settings - standard bold styles
        title_text = title.upper()
        
        # Wrap title
        words = title_text.split()
        lines = []
        current_line = []
        for word in words:
            if len(" ".join(current_line + [word])) * 20 < width - 100:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        # Draw title lines at the top with a black outline
        y_text = 120
        for line in lines[:3]:  # Limit to 3 lines
            # Draw shadow/outline
            for offset_x in [-4, -2, 0, 2, 4]:
                for offset_y in [-4, -2, 0, 2, 4]:
                    draw.text((width // 2 + offset_x, y_text + offset_y), line, fill="#000000", align="center", anchor="ms", font_size=75)
            # Draw main text in yellow
            draw.text((width // 2, y_text), line, fill="#ffcc00", align="center", anchor="ms", font_size=75)
            y_text += 85
            
        # 5. Draw a dramatic badge at the bottom (e.g. "CLIFFHANGER ENDING" or "MUST WATCH")
        badge_text = "CLIFFHANGER ENDING"
        badge_w, badge_h = 600, 100
        badge_x1 = (width - badge_w) // 2
        badge_y1 = height - 250
        
        # Draw red badge background
        draw.rectangle(
            [(badge_x1, badge_y1), (badge_x1 + badge_w, badge_y1 + badge_h)],
            fill=(255, 0, 0, 230),
            outline=(255, 255, 255, 255),
            width=3
        )
        
        # Draw badge text
        draw.text(
            (width // 2, badge_y1 + badge_h // 2 + 10),
            badge_text,
            fill="#ffffff",
            align="center",
            anchor="ms",
            font_size=40
        )
        
        output_path = get_project_file_path(project_id, "thumbnail.png")
        img.save(output_path, "PNG")
        logger.info(f"Saved completed thumbnail to {output_path}")
        return output_path
