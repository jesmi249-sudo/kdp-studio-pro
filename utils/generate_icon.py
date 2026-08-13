from PIL import Image, ImageDraw

def create_icon():
    img = Image.new('RGBA', (256, 256), color=(43, 43, 43, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 236, 236], outline=(0, 120, 215, 255), width=10)
    d.text((128, 128), "KDP", fill=(255, 255, 255, 255), anchor="mm") # Simple text, PIL default font is tiny but it's a placeholder
    
    # Save as ICO
    img.save('assets/icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

if __name__ == '__main__':
    create_icon()
