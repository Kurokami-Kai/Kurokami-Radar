"""Roda um comando do radar.py (pelo codigo) usando os DADOS DA INSTALACAO (%LOCALAPPDATA%\\Kurokami Radar).

Uso: py tools/rodar_instalado.py verificar        (ou testar-notificacao --tipo novo, historico <jogo>...)
Pelo codigo, o radar.py usa a pasta do repositorio (sem banco nem config). Isto so troca os caminhos para os da
instalacao, para testar a versao do codigo com o seu banco de verdade. GRAVA no banco real: feche o Radar antes
e faca um backup (dados/radar.sqlite3) se for algo arriscado."""
import os
import runpy
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from radar import caminhos  # noqa: E402

inst = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Kurokami Radar")
if not os.path.isfile(os.path.join(inst, "dados", "radar.sqlite3")):
    sys.exit("Nao achei a instalacao em %s" % inst)
caminhos.RAIZ_DADOS = inst
caminhos.DADOS = os.path.join(inst, "dados")
caminhos.SONDA = os.path.join(caminhos.DADOS, "sonda")
caminhos.ARQ_CONFIG = os.path.join(inst, "config.json")
for nome, arq in (("ARQ_BANCO", "radar.sqlite3"), ("ARQ_LOG", "radar.log"), ("ARQ_RELATORIO", "alertas.html"),
                  ("ARQ_ICONE", "icone.png"), ("ARQ_CARRINHO", "carrinho.json")):
    setattr(caminhos, nome, os.path.join(caminhos.DADOS, arq))
if hasattr(caminhos, "CAPAS"):
    caminhos.CAPAS = os.path.join(caminhos.DADOS, "capas")
sys.argv = [os.path.join(RAIZ, "radar.py")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
