"""Testa radar/steam_sessao.py sem rede e sem cofre real: QR, renovacao, conta errada, validade, carrinho, sair."""
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import steam_sessao as ss  # noqa: E402

SID = "7656" + "1198000000001"   # inventado
falhas = []
COFRE = {}
CHAMADAS = []


def jwt(sub, exp):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return "%s.%s.sig" % (b({"alg": "none"}), b({"sub": sub, "exp": int(exp)}))


ss.credenciais.ler = lambda n: COFRE.get(n)
ss.credenciais.gravar = lambda n, v: COFRE.__setitem__(n, v) if v else COFRE.pop(n, None)
PERFIL = [SID]
ss._sid_do_perfil = lambda: PERFIL[0]
CART = [{"packageid": 111, "line_item_id": 1}]   # item que o usuario ja tinha
RESP = {}


def falso(servico, metodo, entrada, token=None, post=True):
    CHAMADAS.append((metodo, entrada, token))
    if metodo == "AddItemsToCart":
        for it in entrada["items"]:
            if it.get("packageid") != 999:   # 999 = a Steam recusa
                CART.append({**it, "line_item_id": len(CART) + 1})
        return {}
    if metodo == "GetCart":
        return {"cart": {"line_items": list(CART)}}
    return RESP.get(metodo, {})


ss._servico = falso
CFG = {"pais": "BR", "perfil_steam": ""}
import radar.config as _cfg  # noqa: E402
_cfg.carregar = lambda: dict(CFG)
_cfg.salvar = lambda c: CFG.update(c)


def ok(nome, cond):
    print(("ok   " if cond else "FALHA"), nome)
    if not cond:
        falhas.append(nome)


def zerar():
    COFRE.clear()
    ss._mem.update(access=None, access_exp=0, steamid=None, refresh_exp=0, pendente=None, erro=None)
    CHAMADAS.clear()


# --- login feliz
zerar()
RESP["BeginAuthSessionViaQR"] = {"client_id": "1", "request_id": "r", "challenge_url": "https://s.team/q/1/1", "interval": 5}
ok("QR criado", ss.iniciar_qr() == "https://s.team/q/1/1")
RESP["PollAuthSessionStatus"] = {}
ok("aguardando aprovacao", ss.consultar_qr()["estado"] == "aguardando")
RESP["PollAuthSessionStatus"] = {"new_client_id": "2", "new_challenge_url": "https://s.team/q/1/2"}
ok("QR renovado pela Steam troca a URL", ss.consultar_qr().get("url") == "https://s.team/q/1/2")
ref = jwt(SID, time.time() + 30 * 86400)
acc = jwt(SID, time.time() + 86400)
RESP["PollAuthSessionStatus"] = {"refresh_token": ref, "access_token": acc}
ok("aprovado", ss.consultar_qr()["estado"] == "ok")
ok("refresh foi para o cofre", COFRE.get(ss.COFRE) == ref)
st = ss.estado()
ok("estado: conectado, so os 4 ultimos digitos, ~30 dias", st["conectado"] and st["steamid_final"] == SID[-4:] and 29 <= st["dias"] <= 30)
ok("estado nao devolve token", ref not in json.dumps(st) and acc not in json.dumps(st))
ok("access em memoria", ss.access_token() == acc)

# --- renovacao
ss._mem["access_exp"] = time.time() + 10
novo = jwt(SID, time.time() + 86400) + "x"
RESP["GenerateAccessTokenForApp"] = {"access_token": novo}
try:
    ok("renova perto de vencer", ss.access_token() == novo)
except Exception:
    ok("renova perto de vencer", False)

# --- carrinho: so adiciona e confere; nao mexe no que ja tinha
r = ss.carrinho_adicionar([222, 333], [44])
ok("carrinho: entraram os 3 e confere", r["ok"] and len(r["entraram"]) == 3 and not r["faltaram"])
ok("carrinho: item antigo continua", any(i["packageid"] == 111 for i in CART))
ok("nunca chama remocao", not any(c[0] in ("RemoveItemFromCart", "DeleteCart") for c in CHAMADAS))
n111 = sum(1 for i in CART if i.get("packageid") == 111)
r = ss.carrinho_adicionar([111, 222, 333], [44])
ok("clicar de novo nao duplica: tudo ja estava", r["ok"] and r["entraram"] == [] and r["ja_estavam"] == 4)
ok("clicar de novo: carrinho igual", sum(1 for i in CART if i.get("packageid") == 111) == n111 and sum(1 for i in CART if i.get("packageid") == 222) == 1)
r = ss.carrinho_adicionar([111, 555])
ok("so entra o que falta", r["ok"] and r["entraram"] == [("pacote", 555)] and r["ja_estavam"] == 1)
r = ss.carrinho_adicionar([999])
ok("carrinho: recusado pela Steam aparece em faltaram", not r["ok"] and r["faltaram"] == [("pacote", 999)])

# --- sair
RESP["RevokeToken"] = {}
ok("sair informa que revogou", ss.sair()["revogado"] is True)
ok("sair apaga cofre e memoria", not COFRE and ss._mem["access"] is None and not ss.estado()["conectado"])
ok("sair revogou na Steam", any(c[0] == "RevokeToken" for c in CHAMADAS))

# --- conta diferente da do perfil
zerar()
PERFIL[0] = "7656" + "1198000000002"
ss.iniciar_qr()
RESP["PollAuthSessionStatus"] = {"refresh_token": jwt(SID, time.time() + 86400), "access_token": acc}
res = ss.consultar_qr()
ok("conta diferente: recusa e nao guarda", res["estado"] == "erro" and not COFRE)
ok("conta diferente: revoga o que acabou de criar", any(c[0] == "RevokeToken" for c in CHAMADAS))
ok("mensagem so com 4 digitos", SID not in res["erro"] and "0001" in res["erro"])
PERFIL[0] = SID

# --- sem perfil definido: o SteamID do QR vira o perfil
zerar()
PERFIL[0] = None
CFG["perfil_steam"] = ""
ss.iniciar_qr()
RESP["PollAuthSessionStatus"] = {"refresh_token": jwt(SID, time.time() + 86400), "access_token": acc}
ok("sem perfil: aceita e grava o SteamID como perfil", ss.consultar_qr()["estado"] == "ok" and CFG["perfil_steam"] == SID)
PERFIL[0] = SID

# --- cofre indisponivel: revoga o que criou
zerar()
ss.iniciar_qr()
def _quebra(n, v):
    raise RuntimeError("sem keyring")
_g = ss.credenciais.gravar
ss.credenciais.gravar = _quebra
res = ss.consultar_qr()
ss.credenciais.gravar = _g
ok("cofre falhou: erro claro e sessao revogada", res["estado"] == "erro" and any(c[0] == "RevokeToken" for c in CHAMADAS))

# --- renovacao devolve token de outra conta
zerar()
COFRE[ss.COFRE] = jwt(SID, time.time() + 86400)
RESP["GenerateAccessTokenForApp"] = {"access_token": jwt("7656" + "1198000000009", time.time() + 86400)}
try:
    ss.access_token()
    ok("token de outra conta e recusado", False)
except ss.SessaoErro:
    ok("token de outra conta e recusado", True)

# --- revogacao falha na Steam: avisa
zerar()
COFRE[ss.COFRE] = jwt(SID, time.time() + 86400)
_s = ss._servico
def _rev_falha(servico, metodo, *a, **k):
    if metodo == "RevokeToken":
        raise ss.SessaoErro("Steam fora do ar")
    return _s(servico, metodo, *a, **k)
ss._servico = _rev_falha
ok("sair avisa quando nao conseguiu revogar", ss.sair()["revogado"] is False and not COFRE)
ss._servico = _s

# --- refresh vencido
zerar()
COFRE[ss.COFRE] = jwt(SID, time.time() - 10)
ok("estado: vencido = nao conectado", not ss.estado()["conectado"])
try:
    ss.access_token()
    ok("vencido pede novo QR", False)
except ss.SessaoErro as e:
    ok("vencido pede novo QR e limpa o cofre", "venceu" in str(e) and not COFRE)

# --- sem sessao
zerar()
try:
    ss.access_token()
    ok("sem sessao", False)
except ss.SessaoErro:
    ok("sem sessao pede QR", True)

# --- QR expira
zerar()
ss._mem["pendente"] = {"client_id": "1", "request_id": "r", "url": "u", "inicio": time.time() - 999, "intervalo": 5}
ok("QR velho expira", ss.consultar_qr()["estado"] == "expirou")

print("\nOK" if not falhas else "\nFALHAS: %s" % falhas)
sys.exit(1 if falhas else 0)
