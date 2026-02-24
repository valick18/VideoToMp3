from PIL import Image, ImageDraw

def create_icon():
    # Робимо гарну іконку програмно
    size = (256, 256)
    image = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Малюємо зелене коло (Spotify-style)
    padding = 10
    draw.ellipse([padding, padding, size[0]-padding, size[1]-padding], fill="#1db954")
    
    # Малюємо білу ноту або щось схоже на музику
    # Спрощений символ "плашка"
    draw.rectangle([100, 60, 130, 180], fill="white")
    draw.ellipse([70, 160, 130, 210], fill="white")
    
    image.save('app_icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Іконка створена: app_icon.ico")

if __name__ == "__main__":
    create_icon()
