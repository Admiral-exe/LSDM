"""
Generates high-resolution minimalist logo and multi-size Windows .ico for LSDM.
Laboratory Supply & Dispatch Manager.
"""
from PIL import Image, ImageDraw, ImageFont
import math
import os
from pathlib import Path

def create_lsdm_logo(size=512):
    # Create image with transparent background (RGBA)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size / 2
    radius = size * 0.44

    # Outer rounded squircle background with modern gradient-like subtle layers
    # Base dark slate background with rounded corners
    bg_color = (15, 23, 42, 255)  # #0f172a
    border_color = (30, 41, 59, 255) # #1e293b

    margin = size * 0.04
    corner_r = size * 0.22
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=corner_r,
        fill=bg_color,
        outline=border_color,
        width=int(size * 0.015)
    )

    # Ambient subtle glow ring in background
    glow_color = (6, 182, 212, 35) # Cyan glow
    draw.ellipse(
        [center - radius * 0.8, center - radius * 0.8, center + radius * 0.8, center + radius * 0.8],
        fill=glow_color
    )

    # Minimalist Erlenmeyer Flask + Molecular / Flow Nodes
    # Geometry coordinates for flask
    neck_w = size * 0.09
    neck_top = size * 0.22
    neck_bot = size * 0.38
    base_w = size * 0.32
    base_y = size * 0.70

    # Draw Flask Body (Smooth Modern Outline & Subtle Cyan Fill)
    flask_points = [
        (center - neck_w, neck_top),
        (center + neck_w, neck_top),
        (center + neck_w, neck_bot),
        (center + base_w, base_y - size * 0.05),
        (center + base_w * 0.9, base_y),
        (center - base_w * 0.9, base_y),
        (center - base_w, base_y - size * 0.05),
        (center - neck_w, neck_bot),
    ]

    # Liquid level inside flask (Emerald to Cyan gradient effect)
    liquid_top = size * 0.52
    liquid_points = [
        (center - base_w * 0.58, liquid_top),
        (center + base_w * 0.58, liquid_top),
        (center + base_w * 0.86, base_y - size * 0.04),
        (center + base_w * 0.8, base_y - size * 0.02),
        (center - base_w * 0.8, base_y - size * 0.02),
        (center - base_w * 0.86, base_y - size * 0.04),
    ]
    draw.polygon(liquid_points, fill=(16, 185, 129, 180)) # Emerald Teal translucent

    # Liquid wave meniscus highlight
    draw.line(
        [(center - base_w * 0.58, liquid_top), (center + base_w * 0.58, liquid_top)],
        fill=(56, 189, 248, 240),
        width=int(size * 0.018)
    )

    # Outer Flask Contour (Vibrant Cyan / White)
    contour_color = (56, 189, 248, 255) # Electric Sky Cyan
    line_w = int(size * 0.024)

    # Draw flask outline
    for i in range(len(flask_points)):
        p1 = flask_points[i]
        p2 = flask_points[(i + 1) % len(flask_points)]
        # Skip the top rim for now
        if i == 0:
            continue
        draw.line([p1, p2], fill=contour_color, width=line_w)

    # Flask top lip / rim
    rim_w = neck_w * 1.35
    rim_y = neck_top
    draw.line(
        [(center - rim_w, rim_y), (center + rim_w, rim_y)],
        fill=contour_color,
        width=int(line_w * 1.3)
    )

    # Bubbles / Sample Nodes floating
    node_color = (255, 255, 255, 220)
    draw.ellipse([center - size*0.04, size*0.58, center - size*0.015, size*0.605], fill=node_color)
    draw.ellipse([center + size*0.03, size*0.62, center + size*0.065, size*0.655], fill=(56, 189, 248, 220))
    draw.ellipse([center - size*0.01, size*0.44, center + size*0.02, size*0.47], fill=(16, 185, 129, 230))

    # Dynamic Supply Chain Orbital Track / Pulse Ring around base
    ring_box = [center - size * 0.40, base_y - size * 0.16, center + size * 0.40, base_y + size * 0.10]
    draw.arc(ring_box, start=15, end=165, fill=(16, 185, 129, 220), width=int(size * 0.018))
    # Orbital satellite node
    orbit_x = center + size * 0.36
    orbit_y = base_y - size * 0.02
    draw.ellipse([orbit_x - size*0.025, orbit_y - size*0.025, orbit_x + size*0.025, orbit_y + size*0.025], fill=(52, 211, 153, 255))

    # LSDM Monogram Typography at Bottom Badge
    # Draw a clean, pill-shaped badge for "LSDM"
    badge_w = size * 0.44
    badge_h = size * 0.12
    badge_x = center - badge_w / 2
    badge_y = size * 0.77
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=int(badge_h / 2),
        fill=(30, 41, 59, 240),
        outline=(56, 189, 248, 200),
        width=int(size * 0.008)
    )

    # Try to load a nice font or default to draw clean geometric letters
    try:
        font = ImageFont.truetype("arialbd.ttf", int(size * 0.065))
        # Center text
        bbox = font.getbbox("L S D M")
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = center - tw / 2
        ty = badge_y + (badge_h - th) / 2 - bbox[1] * 0.5
        draw.text((tx, ty), "L S D M", font=font, fill=(248, 250, 252, 255))
    except Exception:
        # Fallback basic font
        draw.text((center - size * 0.12, badge_y + badge_h * 0.25), "LSDM", fill=(255, 255, 255, 255))

    return img

def main():
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    frontend_dir = root / "frontend"

    print("Generating LSDM 512x512 Master Logo...")
    master_img = create_lsdm_logo(512)
    png_path = assets_dir / "logo.png"
    master_img.save(png_path, "PNG")
    print(f"Saved: {png_path}")

    # Generate multi-size .ico (256, 128, 64, 48, 32, 16)
    ico_path = assets_dir / "logo.ico"
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    master_img.save(
        ico_path,
        format="ICO",
        sizes=icon_sizes
    )
    print(f"Saved: {ico_path}")

    # Also save to frontend for favicon and static usage
    frontend_ico = frontend_dir / "favicon.ico"
    master_img.save(frontend_ico, format="ICO", sizes=[(32, 32), (16, 16)])
    print(f"Saved: {frontend_ico}")

    frontend_png = frontend_dir / "logo.png"
    master_img.save(frontend_png, "PNG")
    print(f"Saved: {frontend_png}")

if __name__ == "__main__":
    main()
