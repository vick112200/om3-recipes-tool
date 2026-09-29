from PIL import Image, ImageDraw
import math, os

S = 512
im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=110, fill=(22, 22, 22, 255))

cx = cy = S / 2.0
R, r = 190.0, 118.0
cols = ['#FCF750', '#DBA12A', '#CC1210', '#CD076B', '#970AA0', '#7710E8',
        '#3054E0', '#5392EB', '#83E7EB', '#87EE77', '#9DEE3A', '#CBEE3A']
n = 12
for i, c in enumerate(cols):
    a0 = math.radians(-90 + i * 360.0 / n + 3)
    a1 = math.radians(-90 + (i + 1) * 360.0 / n - 3)
    pts = []
    for t in range(9):
        a = a0 + (a1 - a0) * t / 8.0
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    for t in range(9):
        a = a1 + (a0 - a1) * t / 8.0
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=c)

d.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=(22, 22, 22, 255))

for sz, folder in ((192, 'mipmap-xxxhdpi'), (144, 'mipmap-xxhdpi'),
                   (96, 'mipmap-xhdpi'), (72, 'mipmap-hdpi'), (48, 'mipmap-mdpi')):
    os.makedirs('res/' + folder, exist_ok=True)
    im.resize((sz, sz), Image.LANCZOS).save('res/%s/ic_launcher.png' % folder)

print('icon ok')
