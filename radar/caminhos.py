"""Pastas do app.
- Rodando pelo codigo (py radar.py): tudo fica ao lado do radar.py, como sempre.
- Rodando instalado (.exe): o programa fica em Arquivos de Programas e os SEUS dados em
  %LOCALAPPDATA%\\Kurokami Radar (programa instalado nao pode gravar na propria pasta).
  Na primeira vez, os dados de C:\\Kurokami Radar sao copiados para la."""
import os
import shutil
import sys

CONGELADO = getattr(sys, "frozen", False)
if CONGELADO:
    BASE = os.path.dirname(os.path.abspath(sys.executable))
    RAIZ_DADOS = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Kurokami Radar")
else:
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAIZ_DADOS = BASE

DADOS = os.path.join(RAIZ_DADOS, "dados")
SONDA = os.path.join(DADOS, "sonda")
ARQ_CONFIG = os.path.join(RAIZ_DADOS, "config.json")
ARQ_BANCO = os.path.join(DADOS, "radar.sqlite3")
ARQ_LOG = os.path.join(DADOS, "radar.log")
ARQ_RELATORIO = os.path.join(DADOS, "alertas.html")
ARQ_ICONE = os.path.join(DADOS, "icone.png")
ARQ_CARRINHO = os.path.join(DADOS, "carrinho.json")
PASTA_EXTENSAO = os.path.join(BASE, "extensao")   # extensao do navegador (carrinho da Steam); o instalador copia
ANTIGA = r"C:\Kurokami Radar"


def _migrar():
    """Instalado pela primeira vez: traz banco, config e userdata da versao que rodava pelo codigo."""
    if not CONGELADO or os.path.isfile(ARQ_BANCO):
        return
    origem = os.path.join(ANTIGA, "dados")
    if not os.path.isfile(os.path.join(origem, "radar.sqlite3")):
        return
    os.makedirs(RAIZ_DADOS, exist_ok=True)
    shutil.copytree(origem, DADOS, dirs_exist_ok=True)
    for nome in ("config.json", "userdata.json"):
        if os.path.isfile(os.path.join(ANTIGA, nome)) and not os.path.isfile(os.path.join(RAIZ_DADOS, nome)):
            shutil.copy2(os.path.join(ANTIGA, nome), os.path.join(RAIZ_DADOS, nome))


def garantir():
    _migrar()
    for p in (DADOS, SONDA):
        os.makedirs(p, exist_ok=True)


def achar_userdata(cfg):
    """Procura o userdata.json: na pasta de dados, ao lado do programa, no caminho do config
    ou na pasta do KurokamiPrecos, nessa ordem."""
    candidatos = [os.path.join(RAIZ_DADOS, "userdata.json"), os.path.join(BASE, "userdata.json")]
    extra = (cfg.get("userdata_json") or "").strip()
    if extra:
        candidatos.append(extra if extra.lower().endswith(".json") else os.path.join(extra, "userdata.json"))
    pasta_kp = (cfg.get("pasta_kurokami_precos") or "").strip()
    if pasta_kp:
        candidatos.append(os.path.join(pasta_kp, "userdata.json"))
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None
