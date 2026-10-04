"""Relacao da sua conta Steam com os jogos: seguidos e ignorados (spec 04, B).

Fonte unica desses dados no Radar: nenhum outro modulo le rgFollowedApps nem rgIgnoredApps.
Hoje vem do userdata.json (opcional, manual); a spec 06 (login por QR) troca so esta funcao."""
import json
import os
import threading
from datetime import datetime, timezone

from . import caminhos

_CACHE = {"arq": None, "mtime": None, "valor": None}
_TRAVA = threading.Lock()


def _vazio():
    return {"seguidos": set(), "ignorados": set(), "fonte": None, "quando": None}


def relacao(cfg):
    """{"seguidos": set[int], "ignorados": set[int], "fonte": "userdata" | None, "quando": iso | None}.
    Le o userdata.json achado por caminhos.achar_userdata, com cache pela data de modificacao do arquivo.
    Nunca grava no banco; em qualquer falha devolve conjuntos vazios e fonte None.
    A spec 06 (login por QR) troca so esta funcao."""
    try:
        arq = caminhos.achar_userdata(cfg)
        if not arq:
            return _vazio()
        mtime = os.path.getmtime(arq)
        with _TRAVA:
            if _CACHE["arq"] == arq and _CACHE["mtime"] == mtime:
                return _CACHE["valor"]
        with open(arq, encoding="utf-8-sig") as f:
            u = json.load(f)
        seg = u.get("rgFollowedApps") or []
        ign = u.get("rgIgnoredApps") or {}
        valor = {"seguidos": {int(x) for x in (seg.keys() if isinstance(seg, dict) else seg)},
                 "ignorados": {int(x) for x in (ign.keys() if isinstance(ign, dict) else ign)},
                 "fonte": "userdata",
                 "quando": datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="seconds")}
        with _TRAVA:
            _CACHE.update(arq=arq, mtime=mtime, valor=valor)
        return valor
    except (OSError, ValueError, TypeError, AttributeError):
        return _vazio()


def assinatura(cfg):
    """(arquivo, data de modificacao) do userdata.json: muda quando o arquivo muda (o cache do painel usa)."""
    try:
        arq = caminhos.achar_userdata(cfg)
        return (arq, os.path.getmtime(arq)) if arq else (None, None)
    except OSError:
        return (None, None)
