"""Checagens rapidas antes de entregar uma mudanca. Saida curta: so o que falhou.
Uso: py tools/checar.py"""
import ast
import glob
import os
import re
import shutil
import subprocess
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
falhas, avisos = [], []

# 1. sintaxe Python
for f in glob.glob("radar/*.py") + glob.glob("tools/*.py") + ["radar.py"]:
    try:
        ast.parse(open(f, encoding="utf-8").read())
    except SyntaxError as e:
        falhas.append("sintaxe %s:%s %s" % (f, e.lineno, e.msg))

# 2. JavaScript do painel e da ponte
node = shutil.which("node")
if node:
    for arq, extrair in (("radar/painel.html", True), ("radar/ponte.user.js", False)):
        txt = open(arq, encoding="utf-8").read()
        js = txt[txt.index("<script>") + 8:txt.rindex("</script>")] if extrair else txt
        r = subprocess.run([node, "-e", "new Function(require('fs').readFileSync(0,'utf8'))"], input=js,
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            falhas.append("JS %s: %s" % (arq, (r.stderr.strip().splitlines() or ["?"])[-1][:160]))
else:
    avisos.append("node nao encontrado: JS nao verificado")

# 3. versao do servidor == versao da pagina
v = re.search(r'VERSAO = "([^"]+)"', open("radar/__init__.py", encoding="utf-8").read()).group(1)
vp = re.search(r"VERSAO_PAGINA='([^']+)'", open("radar/painel.html", encoding="utf-8").read())
if not vp or vp.group(1) != v:
    falhas.append("VERSAO (%s) != VERSAO_PAGINA (%s)" % (v, vp.group(1) if vp else "?"))

# 4. arquivos que o .exe precisa ler estao no --add-data
for dado in ("painel.html", "ponte.user.js"):
    for build in (".github/workflows/gerar-instalador.yml", "gerar_setup.bat"):
        if os.path.isfile(build) and dado not in open(build, encoding="utf-8").read():
            falhas.append("%s fora do --add-data de %s" % (dado, build))

# 5. nada pessoal nos arquivos versionados
pessoal = re.compile(r"7656119\d{10}|steamLoginSecure|\b[0-9A-F]{32}\b")
for f in glob.glob("**/*", recursive=True):
    if os.path.isdir(f) or f.startswith(("dados", ".git")) or f in ("config.json", "userdata.json", os.path.join("tools", "checar.py")) \
            or f.endswith((".png", ".ico", ".exe", ".zip")):
        continue
    try:
        m = pessoal.search(open(f, encoding="utf-8").read())
    except (UnicodeDecodeError, OSError):
        continue
    if m:
        falhas.append("possivel dado pessoal em %s: %s..." % (f, m.group(0)[:8]))
padrao = open("radar/config.py", encoding="utf-8").read()
if re.search(r'"perfil_steam":\s*"[^"]+"', padrao):
    falhas.append("config.PADRAO tem perfil_steam preenchido")

print("versao %s" % v)
for a in avisos:
    print("aviso: " + a)
if falhas:
    print("FALHOU (%d):" % len(falhas))
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
print("ok: sintaxe, JS, versao, --add-data e dados pessoais")
