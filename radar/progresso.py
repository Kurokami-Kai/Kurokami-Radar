"""Em que parte da checagem o Hunter esta (para o painel e o icone da bandeja).
Duas pistas (0.18.2): ESTADO e a rapida; LENTA e a do segundo plano (catalogo, biblioteca, historicos). Cada funcao grava
na pista da thread que a chamou (rede.e_lenta), entao o codigo da coleta nao precisa saber qual e."""
import collections
import threading
import time

from . import rede

_lock = threading.Lock()


def _novo():
    return {"ativo": False, "modo": None, "etapa": None, "atual": 0, "total": 0, "inicio": None,
            "etapa_inicio": None, "log": collections.deque(maxlen=60), "ultima": None}


ESTADO = _novo()
LENTA = _novo()


def _alvo():
    return LENTA if rede.e_lenta() else ESTADO


def iniciar(modo):
    with _lock:
        e = _alvo()
        e.update(ativo=True, modo=modo, etapa="Começando", atual=0, total=0, inicio=time.time(), etapa_inicio=time.time())
        e["log"].clear()


def etapa(nome, total=0):
    with _lock:
        _alvo().update(etapa=nome, atual=0, total=total or 0, etapa_inicio=time.time())


def passo(atual, total=None):
    with _lock:
        e = _alvo()
        e["atual"] = atual
        if total is not None:
            e["total"] = total


def linha(msg):
    """Cada linha do log tambem vira progresso: linha sem recuo = etapa nova."""
    with _lock:
        _alvo()["log"].append(time.strftime("%H:%M:%S ") + msg)
    if msg and not msg.startswith(" ") and not msg.startswith("!!"):
        etapa(msg.split(" (")[0].rstrip("."))


def fim(ok=True, resumo=None, registrar=True):
    """registrar=False: a rodada nao fez nada (pista lenta sem trabalho): nao troca o "ultima"."""
    with _lock:
        e = _alvo()
        dur = time.time() - (e["inicio"] or time.time())
        e.update(ativo=False, etapa=None, atual=0, total=0)
        if registrar:
            e["ultima"] = {"modo": e["modo"], "ok": ok, "duracao": round(dur), "fim": time.time(), "resumo": resumo}


def _foto(e):
    d = {k: v for k, v in e.items() if k != "log"}
    d["log"] = list(e["log"])[-25:]
    if d["inicio"]:
        d["decorrido"] = round(time.time() - d["inicio"])
    return d


def foto():
    with _lock:
        d = _foto(ESTADO)
        d["lenta"] = _foto(LENTA)
        return d
