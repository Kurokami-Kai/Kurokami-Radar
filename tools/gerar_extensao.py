"""Prepara a extensao do navegador para a loja do Edge (Microsoft Partner Center).

Uso: py tools/gerar_extensao.py
- extensao/icones/*.png (16, 32, 48, 128): o mesmo desenho da bandeja; ficam no Git (a extensao precisa deles).
- output/kurokami-radar-extensao-<versao>.zip: o pacote para enviar (manifest na raiz do ZIP).
- output/loja-edge-logo-300.png: o logo da pagina da loja (300x300).
Textos da pagina da loja e respostas do formulario: docs/loja-edge.md."""
import json
import os
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from radar.bandeja import desenhar_icone  # noqa: E402

EXT = os.path.join(RAIZ, "extensao")
SAIDA = os.path.join(RAIZ, "output")
os.makedirs(os.path.join(EXT, "icones"), exist_ok=True)
os.makedirs(SAIDA, exist_ok=True)

base = desenhar_icone().resize((512, 512))
for t in (16, 32, 48, 128):
    base.resize((t, t)).save(os.path.join(EXT, "icones", "%d.png" % t))
base.resize((300, 300)).save(os.path.join(SAIDA, "loja-edge-logo-300.png"))

versao = json.load(open(os.path.join(EXT, "manifest.json"), encoding="utf-8"))["version"]
zip_ = os.path.join(SAIDA, "kurokami-radar-extensao-%s.zip" % versao)
with zipfile.ZipFile(zip_, "w", zipfile.ZIP_DEFLATED) as z:
    for pasta, _, arqs in os.walk(EXT):
        for a in sorted(arqs):
            caminho = os.path.join(pasta, a)
            z.write(caminho, os.path.relpath(caminho, EXT).replace(os.sep, "/"))
print("ok: %s e o logo em %s" % (zip_, SAIDA))
