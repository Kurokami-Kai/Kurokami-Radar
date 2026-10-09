"""Em que parte da checagem o Hunter esta (para o painel e o icone da bandeja)."""
import collections
import threading
import time

_lock = threading.Lock()
ESTADO = {"ativo": False, "modo": None, "etapa": None, "atual": 0, "total": 0, "inicio": None,
          "etapa_inicio": None, "log": collections.deque(maxlen=60), "ultima": None}


def iniciar(modo):
    with _lock:
        ESTADO.update(ativo=True, modo=modo, etapa="Começando", atual=0, total=0, inicio=time.time(), etapa_inicio=time.time())
        ESTADO["log"].clear()


def etapa(nome, total=0):
    with _lock:
        ESTADO.update(etapa=nome, atual=0, total=total or 0, etapa_inicio=time.time())


def passo(atual, total=None):
    with _lock:
        ESTADO["atual"] = atual
        if total is not None:
            ESTADO["total"] = total


def linha(msg):
    """Cada linha do log tambem vira progresso: linha sem recuo = etapa nova."""
    with _lock:
        ESTADO["log"].append(time.strftime("%H:%M:%S ") + msg)
    if msg and not msg.startswith(" ") and not msg.startswith("!!"):
        etapa(msg.split(" (")[0].rstrip("."))


def fim(ok=True, resumo=None):
    with _lock:
        dur = time.time() - (ESTADO["inicio"] or time.time())
        ESTADO.update(ativo=False, etapa=None, atual=0, total=0,
                      ultima={"modo": ESTADO["modo"], "ok": ok, "duracao": round(dur), "fim": time.time(), "resumo": resumo})


def foto():
    with _lock:
        d = {k: v for k, v in ESTADO.items() if k != "log"}
        d["log"] = list(ESTADO["log"])[-25:]
        if d["inicio"]:
            d["decorrido"] = round(time.time() - d["inicio"])
        return d
