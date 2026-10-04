"""Sobe o painel numa COPIA do banco real, sem coleta e sem rede (para ver o visual e tirar prints).

Uso: py tools/painel_copia.py [--porta 8799] [--banco CAMINHO] [--config CAMINHO]
Abre em http://127.0.0.1:<porta>/kurokami (use #vale ou #lista no fim para abrir uma aba). Ctrl+C encerra e apaga a copia.
Prints sem instalar nada (Edge headless):
  msedge --headless --disable-gpu --virtual-time-budget=15000 --window-size=1280,2200 --screenshot=ARQ.png URL"""
import argparse
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import caminhos  # noqa: E402
from tools.backtest_selo import achar_banco  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--porta", type=int, default=8799)
    ap.add_argument("--banco"); ap.add_argument("--config")
    a = ap.parse_args()
    origem, cfg_arq = (a.banco, a.config) if a.banco else achar_banco()
    tmp = tempfile.mkdtemp(prefix="kr-painel-")
    try:
        shutil.copy2(origem, os.path.join(tmp, "radar.sqlite3"))
        shutil.copy2(a.config or cfg_arq, os.path.join(tmp, "config.json"))
        carr = os.path.join(os.path.dirname(origem), "carrinho.json")
        caminhos.ARQ_BANCO = os.path.join(tmp, "radar.sqlite3")
        caminhos.ARQ_CONFIG = os.path.join(tmp, "config.json")
        caminhos.DADOS = caminhos.SONDA = os.path.join(tmp, "dados")
        caminhos.ARQ_CARRINHO = os.path.join(tmp, "carrinho.json")
        if os.path.isfile(carr):
            shutil.copy2(carr, caminhos.ARQ_CARRINHO)
        from radar import painel
        painel.ARQ_TOKEN = os.path.join(tmp, "painel_token.txt")
        painel.PORTAS = (a.porta,)
        painel.rede_local = lambda: False  # so neste PC
        painel.iniciar()
        print("painel na copia: http://127.0.0.1:%d%s  (Ctrl+C encerra)" % (painel.PORTA, painel.CAMINHO), flush=True)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
