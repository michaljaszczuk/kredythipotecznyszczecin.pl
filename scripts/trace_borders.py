import cv2
import numpy as np

SRC = r"D:\poligon\directory websites\kredythipotecznyszczecin.pl\szczecin_borders.png"
OUT = r"D:\poligon\directory websites\kredythipotecznyszczecin.pl\website\public\szczecin-borders.svg"

img = cv2.imread(SRC, cv2.IMREAD_UNCHANGED)

# Use alpha if present to know what's "ink" vs transparent/white background
if img.shape[2] == 4:
    bgr = img[:, :, :3]
    alpha = img[:, :, 3]
else:
    bgr = img
    alpha = None

gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
# Ink = dark pixels
_, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

if alpha is not None:
    mask = cv2.bitwise_and(mask, mask, mask=(alpha > 10).astype(np.uint8) * 255)

# Thicken the traced lines (source strokes are ~3px at native res)
DILATE_PX = 3
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (DILATE_PX * 2 + 1, DILATE_PX * 2 + 1))
mask = cv2.dilate(mask, kernel)

h, w = mask.shape

contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_L1)

path_parts = []
for cnt in contours:
    if len(cnt) < 3:
        continue
    cnt = cv2.approxPolyDP(cnt, 0.6, True)
    if len(cnt) < 3:
        continue
    pts = cnt.reshape(-1, 2)
    d = "M " + " L ".join(f"{x} {y}" for x, y in pts) + " Z"
    path_parts.append(d)

path_data = " ".join(path_parts)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" fill="currentColor" fill-rule="evenodd">
<path d="{path_data}"/>
</svg>
'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print("wrote", OUT, "contours:", len(path_parts))
