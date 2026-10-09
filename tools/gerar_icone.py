"""Gera assets/radar.ico (usado no .exe e no instalador) a partir do mesmo desenho da bandeja."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar.bandeja import desenhar_icone  # noqa: E402

os.makedirs("assets", exist_ok=True)
img = desenhar_icone(tam=256)
img.save("assets/radar.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("assets/radar.ico gerado")
