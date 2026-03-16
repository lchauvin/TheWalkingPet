"""Generate a paw print icon for TheWalkingPet app."""
from PIL import Image, ImageDraw

SIZE = 1024
BG_COLOR = (255, 87, 34)   # Deep orange
PAW_COLOR = (255, 255, 255) # White

img = Image.new("RGBA", (SIZE, SIZE), BG_COLOR)
draw = ImageDraw.Draw(img)

cx, cy = SIZE // 2, SIZE // 2

# Main pad (large oval, center-bottom)
pad_w, pad_h = 220, 200
draw.ellipse(
    [cx - pad_w, cy - pad_h // 2 + 80, cx + pad_w, cy + pad_h + 80],
    fill=PAW_COLOR,
)

# Four toe pads
toes = [
    (-230, -130, 110, 130),  # far left
    (-110, -220, 100, 120),  # center-left
    ( 110, -220, 100, 120),  # center-right
    ( 230, -130, 110, 130),  # far right
]
for tx, ty, tw, th in toes:
    draw.ellipse(
        [cx + tx - tw // 2, cy + ty - th // 2,
         cx + tx + tw // 2, cy + ty + th // 2],
        fill=PAW_COLOR,
    )

img.save("mobile/assets/icon.png")
img.save("mobile/assets/splash.png")
print("Generated mobile/assets/icon.png and splash.png")
