import os
from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = os.path.join('assets', 'icons')
os.makedirs(ICONS_DIR, exist_ok=True)

icons = {
    'dashboard.png': 'D',
    'projects.png': 'P',
    'metadata.png': 'M',
    'assets.png': 'A',
    'coloring.png': 'C',
    'interior.png': 'I',
    'cover.png': 'V',
    'planner.png': 'L',
    'storybook.png': 'S',
    'activity.png': 'T',
    'export.png': 'E',
    'compliance.png': 'K',
    'settings.png': 'O',
    'help.png': '?',
    'new.png': '+',
    'open.png': '^',
    'save.png': 'S',
    'undo.png': '<',
    'redo.png': '>'
}

for name, letter in icons.items():
    img = Image.new('RGBA', (24, 24), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    # Draw a rounded rect as a background for the icon
    d.rounded_rectangle([2, 2, 22, 22], radius=4, fill=(100, 100, 100, 200))
    # Draw the letter centered
    d.text((12, 12), letter, fill=(255, 255, 255, 255), anchor="mm")
    
    img.save(os.path.join(ICONS_DIR, name))

print("Icons generated successfully.")
