"""Testa radar/steam_openid.py sem rede: o que a validacao do "Entrar pela Steam" aceita e recusa."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import steam_openid as so  # noqa: E402

BASE = "http://localhost"
SID = "7656" + "1198000000001"   # inventado (partido para o checar.py nao confundir com dado pessoal)
falhas = []


def volta(state, **mudar):
    agora = time.gmtime()
    p = {"s": [state], "openid.ns": [so.NS], "openid.mode": ["id_res"], "openid.op_endpoint": [so.ENDPOINT],
         "openid.claimed_id": ["https://steamcommunity.com/openid/id/" + SID],
         "openid.identity": ["https://steamcommunity.com/openid/id/" + SID],
         "openid.return_to": ["%s/kurokami/steam/retorno?s=%s" % (BASE, state)],
         "openid.response_nonce": [time.strftime("%Y-%m-%dT%H:%M:%SZ", agora) + "abc" + state[:4]],
         "openid.signed": ["signed,op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle"],
         "openid.sig": ["x"], "openid.assoc_handle": ["h"]}
    for k, v in mudar.items():
        if v is None:
            p.pop(k, None)
        else:
            p[k] = [v]
    return p


def novo():
    u = so.url_de_entrada(BASE)
    return u.split("openid.return_to=")[1].split("%3Fs%3D")[1].split("&")[0]


def espera(nome, q, ok, confirmar=lambda p: True):
    try:
        r = so.concluir(q, BASE, confirmar=confirmar)
        res = r == SID
    except so.LoginInvalido:
        res = False
    if res != ok:
        falhas.append(nome)
    print(("ok   " if res == ok else "FALHA"), nome)


s = novo()
espera("volta valida", volta(s), True)
espera("reenviar o mesmo retorno (state e nonce usados)", volta(s), False)
espera("state desconhecido", volta("inventado"), False)
s = novo(); espera("Steam recusa (is_valid false)", volta(s), False, lambda p: False)
s = novo(); espera("claimed_id que nao e da Steam", volta(s, **{"openid.claimed_id": "https://evil.example/openid/id/" + SID}), False)
s = novo(); espera("identity diferente do claimed_id", volta(s, **{"openid.identity": "https://steamcommunity.com/openid/id/" + SID[:-1] + "2"}), False)
s = novo(); espera("op_endpoint de outro servidor", volta(s, **{"openid.op_endpoint": "https://evil.example/openid/login"}), False)
s = novo(); espera("return_to de outro state", volta(s, **{"openid.return_to": BASE + "/kurokami/steam/retorno?s=outro"}), False)
s = novo(); espera("campo nao assinado (return_to fora do signed)", volta(s, **{"openid.signed": "signed,claimed_id,identity,response_nonce,op_endpoint"}), False)
s = novo(); espera("nonce velho", volta(s, **{"openid.response_nonce": "2020-01-01T00:00:00Zabc"}), False)
s = novo(); espera("sem nonce", volta(s, **{"openid.response_nonce": None}), False)
s = novo(); espera("SteamID com tamanho errado", volta(s, **{"openid.claimed_id": "https://steamcommunity.com/openid/id/123", "openid.identity": "https://steamcommunity.com/openid/id/123"}), False)
s = novo()
q = volta(s)
try:
    so.concluir(q, BASE, confirmar=lambda p: (_ for _ in ()).throw(OSError("sem rede")))
    falhas.append("sem rede deveria falhar")
except so.LoginInvalido:
    print("ok    sem rede para confirmar -> recusa")
s = novo(); q = volta(s)
agora = time.time() + 400
try:
    so.concluir(q, BASE, confirmar=lambda p: True, agora=agora)
    falhas.append("state expirado")
except so.LoginInvalido:
    print("ok    state expirado (>5 min)")
print("\nOK" if not falhas else "\nFALHAS: %s" % falhas)
sys.exit(1 if falhas else 0)
