"""Conta Steam por QR (opcional; spec 06, Nivel 2). Sem entrar, o Radar funciona como sempre.
Seguranca (docs/decisoes.md, "Login Steam"):
- o Radar nunca ve a senha: o usuario aprova no app da Steam;
- o refresh token (30 dias) fica SO no Gerenciador de Credenciais do Windows (radar/credenciais.py);
- o access token (~24 h) fica SO em memoria; nada de token em arquivo, log, banco ou config;
- so HTTPS para api.steampowered.com; so a propria conta (o SteamID do token tem de ser o do perfil_steam).
platform_type=3 (app movel): e o unico cujo refresh token renova o access token."""
import base64
import json
import threading
import time
import urllib.parse

from . import credenciais
from .rede import RITMO, http_json

API = "https://api.steampowered.com/"
COFRE = "steam_refresh"
PLATAFORMA = 3
ANTECEDENCIA = 120   # renova o access token 2 min antes de vencer
VALIDADE_QR = 180    # o QR some do painel depois de 3 min sem aprovar

_lock = threading.RLock()
_mem = {"access": None, "access_exp": 0, "steamid": None, "refresh_exp": 0, "pendente": None, "erro": None}


class SessaoErro(Exception):
    pass


def _jwt(tok):
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def _servico(servico, metodo, entrada, token=None, post=True):
    url = "%s%s/%s/v1/" % (API, servico, metodo)
    params = {"input_json": json.dumps(entrada, separators=(",", ":"))}
    if token:
        params["access_token"] = token
    try:
        if post:
            r = http_json(url, form=params, ritmo=RITMO["steam"], tentativas=2)
        else:
            r = http_json(url + "?" + urllib.parse.urlencode(params), ritmo=RITMO["steam"], tentativas=2)
    except Exception as e:   # nunca deixa a URL (com token) subir na mensagem
        raise SessaoErro("A Steam não respondeu (%s)." % type(e).__name__)
    return (r or {}).get("response", r) or {}


def _guardar_access(access):
    j = _jwt(access)
    _mem["access"], _mem["access_exp"] = access, j.get("exp", 0)


def _sid_do_perfil():
    from . import config
    p = str(config.carregar().get("perfil_steam") or "").strip().rstrip("/").split("/")[-1]
    return p if p.isdigit() and len(p) == 17 else None


# ------------------------------------------------------------------ login por QR
def iniciar_qr():
    """Pede um QR novo. Devolve a URL do desafio (o painel desenha). Substitui qualquer QR pendente."""
    nome = "Kurokami Radar"
    r = _servico("IAuthenticationService", "BeginAuthSessionViaQR",
                 {"device_friendly_name": nome, "platform_type": PLATAFORMA, "website_id": "Store",
                  "device_details": {"device_friendly_name": nome, "platform_type": PLATAFORMA}})
    if not r.get("challenge_url") or not r.get("client_id"):
        raise SessaoErro("A Steam não criou o QR. Tente de novo.")
    with _lock:
        _mem["erro"] = None
        _mem["pendente"] = {"client_id": r["client_id"], "request_id": r["request_id"], "url": r["challenge_url"],
                            "inicio": time.time(), "intervalo": max(float(r.get("interval") or 5), 2.0)}
    return r["challenge_url"]


def consultar_qr():
    """Uma consulta ao Poll. {estado: aguardando|ok|expirou|nenhum|erro, url?, erro?}. O painel chama a cada ~3 s."""
    with _lock:
        pen = _mem["pendente"]
        if not pen:
            return {"estado": "nenhum"}
        if time.time() - pen["inicio"] > VALIDADE_QR:
            _mem["pendente"] = None
            return {"estado": "expirou"}
    try:
        p = _servico("IAuthenticationService", "PollAuthSessionStatus",
                     {"client_id": pen["client_id"], "request_id": pen["request_id"]})
    except SessaoErro as e:
        return {"estado": "aguardando", "url": pen["url"], "aviso": str(e)}
    with _lock:
        if p.get("new_client_id"):   # a Steam troca o desafio a cada ~20 s
            pen["client_id"] = p["new_client_id"]
            if p.get("new_challenge_url"):
                pen["url"] = p["new_challenge_url"]
        if p.get("refresh_token"):
            return _concluir(p["refresh_token"], p.get("access_token"))
    return {"estado": "aguardando", "url": pen["url"]}


def _concluir(refresh, access):
    jr = _jwt(refresh)
    sid = str(jr.get("sub") or "")
    esperado = _sid_do_perfil()
    if esperado and sid != esperado:
        _revogar(refresh)   # conta diferente da do perfil: desfaz e avisa
        _mem["pendente"] = None
        _mem["erro"] = "Essa conta Steam (…%s) não é a do perfil em uso (…%s). Entre pelo OpenID com a conta certa ou use o QR dela." % (sid[-4:], esperado[-4:])
        return {"estado": "erro", "erro": _mem["erro"]}
    try:
        credenciais.gravar(COFRE, refresh)
    except Exception:   # sem cofre (keyring ausente): nao deixa uma sessao viva na Steam sem ter onde guarda-la
        _revogar(refresh)
        _mem["pendente"] = None
        _mem["erro"] = "Não consegui guardar a sessão no cofre do Windows. Instale o keyring (py -m pip install keyring)."
        return {"estado": "erro", "erro": _mem["erro"]}
    if not esperado:   # sem perfil definido: o SteamID do QR vira o perfil (como no "Entrar pela Steam")
        from . import config
        cfg = config.carregar()
        cfg["perfil_steam"] = sid
        config.salvar(cfg)
    _mem.update(steamid=sid, refresh_exp=jr.get("exp", 0), pendente=None, erro=None)
    if access:
        _guardar_access(access)
    else:
        _renovar()
    return {"estado": "ok"}


def _revogar(refresh):
    """True se a Steam confirmou a revogacao."""
    try:
        _servico("IAuthenticationService", "RevokeToken", {"token": refresh, "revoke_action": 1})
        return True
    except SessaoErro:
        return False


def _pais():
    from . import config
    return str(config.carregar().get("pais") or "BR")


def _renovar():
    refresh = credenciais.ler(COFRE)
    if not refresh:
        raise SessaoErro("Entre com o QR da Steam.")
    try:
        jr = _jwt(refresh)
    except Exception:
        credenciais.gravar(COFRE, "")
        raise SessaoErro("Sessão da Steam inválida. Entre de novo com o QR.")
    if jr.get("exp", 0) <= time.time():
        credenciais.gravar(COFRE, "")
        _mem.update(access=None, access_exp=0, steamid=None)
        raise SessaoErro("A sessão da Steam venceu (dura ~30 dias). Entre de novo com o QR.")
    r = _servico("IAuthenticationService", "GenerateAccessTokenForApp",
                 {"refresh_token": refresh, "steamid": str(jr["sub"])})
    if not r.get("access_token"):
        raise SessaoErro("A Steam não renovou a sessão. Entre de novo com o QR.")
    if str(_jwt(r["access_token"]).get("sub")) != str(jr["sub"]):
        raise SessaoErro("A Steam devolveu uma sessão de outra conta. Entre de novo com o QR.")
    _mem["steamid"], _mem["refresh_exp"] = str(jr["sub"]), jr.get("exp", 0)
    _guardar_access(r["access_token"])


def access_token():
    """Access token valido (renova sozinho). Levanta SessaoErro se nao ha sessao ou ela venceu."""
    with _lock:
        if not _mem["access"] or _mem["access_exp"] - time.time() < ANTECEDENCIA:
            _renovar()
        return _mem["access"]


def estado():
    """Para o painel (sem segredo): conectado?, final do SteamID, dias que faltam."""
    with _lock:
        refresh = credenciais.ler(COFRE)
        if not refresh:
            return {"conectado": False, "erro": _mem["erro"], "pendente": bool(_mem["pendente"])}
        try:
            jr = _jwt(refresh)
        except Exception:
            return {"conectado": False, "erro": "Sessão inválida."}
        resta = jr.get("exp", 0) - time.time()
        if resta <= 0:
            return {"conectado": False, "erro": "A sessão da Steam venceu. Entre de novo com o QR."}
        return {"conectado": True, "steamid_final": str(jr.get("sub", ""))[-4:], "dias": int(resta // 86400),
                "vence_em_breve": resta < 5 * 86400, "pendente": bool(_mem["pendente"])}


def sair():
    """Revoga na Steam e apaga do cofre e da memoria."""
    with _lock:
        refresh = credenciais.ler(COFRE)
        revogado = _revogar(refresh) if refresh else True
        if refresh:
            credenciais.gravar(COFRE, "")
        _mem.update(access=None, access_exp=0, steamid=None, refresh_exp=0, pendente=None, erro=None)
    return {"ok": True, "revogado": revogado}


# ------------------------------------------------------------------ carrinho da conta
def _cart(token):
    r = _servico("IAccountCartService", "GetCart", {"user_country": _pais()}, token, post=False)
    return (r.get("cart") or {}).get("line_items") or []


def carrinho_ler():
    """[(packageid, bundleid, line_item_id)] do carrinho da conta."""
    return [(i.get("packageid") or 0, i.get("bundleid") or 0, i.get("line_item_id")) for i in _cart(access_token())]


def carrinho_adicionar(pacotes=(), bundles=()):
    """Adiciona SO o que ainda nao esta no carrinho (clicar duas vezes nao duplica) e CONFERE lendo de volta.
    Devolve {ok, entraram: [...novos], ja_estavam: n, faltaram: [...]}. Nao remove nada que o usuario ja tinha."""
    tok = access_token()
    pedidos = [("pacote", int(p)) for p in pacotes] + [("bundle", int(b)) for b in bundles]
    if not pedidos:
        return {"ok": True, "entraram": [], "ja_estavam": 0, "faltaram": []}
    chave = lambda i: (i.get("packageid") or 0, i.get("bundleid") or 0)
    antes = {chave(i) for i in _cart(tok)}
    par = lambda x: (x[1], 0) if x[0] == "pacote" else (0, x[1])
    novos = [x for x in pedidos if par(x) not in antes]
    if novos:
        itens = [{"packageid": x[1]} if x[0] == "pacote" else {"bundleid": x[1]} for x in novos]
        _servico("IAccountCartService", "AddItemsToCart", {"user_country": _pais(), "items": itens}, tok)
    depois = {chave(i) for i in _cart(tok)}
    faltaram = [x for x in pedidos if par(x) not in depois]
    return {"ok": not faltaram, "entraram": [x for x in novos if par(x) in depois],
            "ja_estavam": len(pedidos) - len(novos), "faltaram": faltaram}
