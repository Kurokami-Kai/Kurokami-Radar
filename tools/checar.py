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

# 2. JavaScript do painel
node = shutil.which("node")
if node:
    for arq, extrair in (("radar/painel.html", True), ("radar/ofertas.html", True), ("radar/biblioteca.html", True)):
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
for dado in ("painel.html", "ofertas.html", "biblioteca.html"):
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

# 6. arquivos pessoais fora do Git: .gitignore com as entradas e nada rastreado
PESSOAIS = {"config.json": ("config.json", "/config.json"), "userdata.json": ("userdata.json", "/userdata.json"),
            "dados/": ("dados", "dados/", "/dados", "/dados/", "dados/*", "dados/**")}
if not os.path.isfile(".gitignore"):
    falhas.append(".gitignore nao existe")
else:
    linhas = {l.strip() for l in open(".gitignore", encoding="utf-8")}
    for entrada, formas in PESSOAIS.items():
        if not linhas.intersection(formas):
            falhas.append(".gitignore sem a entrada %s" % entrada)
git = shutil.which("git")
if git:
    r = subprocess.run([git, "ls-files", "--", "config.json", "userdata.json", "dados"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        falhas.append("git ls-files falhou: %s" % (r.stderr.strip()[:160] or "?"))
    for f in r.stdout.splitlines():
        falhas.append("arquivo pessoal rastreado pelo Git: %s (git rm --cached)" % f)
else:
    avisos.append("git nao encontrado: arquivos rastreados nao verificados")

# 7. testes sinteticos da pilula de piso e do Lendario (sem rede, < 1 s)
r = subprocess.run([sys.executable, os.path.join("tools", "testar_piso.py")], capture_output=True, text=True, encoding="utf-8")
if r.returncode:
    falhas += [l for l in r.stdout.splitlines() if l.startswith("FALHOU")] or ["testar_piso: %s" % (r.stderr.strip()[-160:] or "?")]

# 8. validacao do "Entrar pela Steam" (OpenID), sem rede
r = subprocess.run([sys.executable, os.path.join("tools", "testar_openid.py")], capture_output=True, text=True, encoding="utf-8")
if r.returncode:
    falhas += [l for l in r.stdout.splitlines() if l.startswith("FALHA")] or ["testar_openid: %s" % (r.stderr.strip()[-160:] or "?")]

# 9. extensao do navegador (carrinho da Steam): manifest valido, arquivos citados existem, JS ok, vai no instalador
import json  # noqa: E402
try:
    man = json.load(open("extensao/manifest.json", encoding="utf-8"))
    if len(man.get("description", "")) > 132:  # limite das lojas do Edge e do Chrome
        falhas.append("extensao: description com %d caracteres (maximo 132)" % len(man["description"]))
    js_ext = [man["background"]["service_worker"]] + [j for c in man["content_scripts"] for j in c["js"]]
    for j in js_ext:
        if not os.path.isfile(os.path.join("extensao", j)):
            falhas.append("extensao: %s citado no manifest nao existe" % j)
        elif node:
            r = subprocess.run([node, "--check", os.path.join("extensao", j)], capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                falhas.append("JS extensao/%s: %s" % (j, (r.stderr.strip().splitlines() or ["?"])[-1][:160]))
except (OSError, ValueError, KeyError) as e:
    falhas.append("extensao/manifest.json invalido: %s" % e)
if "extensao\\*" not in open("installer.iss", encoding="utf-8-sig").read():
    falhas.append("installer.iss nao copia a pasta extensao")

print("versao %s" % v)
for a in avisos:
    print("aviso: " + a)
if falhas:
    print("FALHOU (%d):" % len(falhas))
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
print("ok: sintaxe, JS, versao, --add-data, dados pessoais, .gitignore, testar_piso, testar_openid e extensao")
