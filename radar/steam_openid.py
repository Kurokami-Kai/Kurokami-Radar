"""Entrar pela Steam (OpenID 2.0), como no ITAD, na GG.deals e na SteamDB.
O usuario confirma na pagina da propria Steam; o Hunter so recebe o SteamID. Nenhuma senha, token ou cookie
da Steam chega ao Hunter. Tudo em memoria (state e nonces); so o SteamID vai para o config."""
import calendar
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://steamcommunity.com/openid/login"
NS = "http://specs.openid.net/auth/2.0"
RE_ID = re.compile(r"^https://steamcommunity\.com/openid/id/(\d{17})$")
RE_NONCE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)(.{0,100})$")
VALIDADE = 300  # segundos: tempo para confirmar na Steam e idade maxima do nonce

_lock = threading.Lock()
_pendentes = {}   # state -> instante de criacao (uso unico)
_nonces = {}      # response_nonce -> instante em que foi visto


class LoginInvalido(Exception):
    pass


def _limpar(agora):
    for d in (_pendentes, _nonces):
        for k in [k for k, t in d.items() if agora - t > 2 * VALIDADE]:
            del d[k]


def _retorno(base, state):
    return "%s/kurokami/steam/retorno?s=%s" % (base, state)


def url_de_entrada(base):
    """URL da pagina de login da Steam. `base` = http://localhost[:porta], montada pelo servidor (nunca pelo cabecalho Host)."""
    state = secrets.token_urlsafe(24)
    agora = time.time()
    with _lock:
        _limpar(agora)
        while len(_pendentes) >= 20:   # teto: um site aberto no navegador nao pode encher a memoria
            del _pendentes[min(_pendentes, key=_pendentes.get)]
        _pendentes[state] = agora
    p = {"openid.ns": NS, "openid.mode": "checkid_setup", "openid.return_to": _retorno(base, state),
         "openid.realm": base, "openid.identity": NS + "/identifier_select", "openid.claimed_id": NS + "/identifier_select"}
    return ENDPOINT + "?" + urllib.parse.urlencode(p)


def _confirmar_na_steam(params):
    corpo = dict(params)
    corpo["openid.mode"] = "check_authentication"
    req = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode(corpo).encode(),
                                 headers={"User-Agent": "KurokamiRadar/0.1", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as r:
        txt = r.read(4096).decode("utf-8", "replace")
    return "is_valid:true" in txt.split()


def concluir(query, base, confirmar=_confirmar_na_steam, agora=None):
    """Valida a volta da Steam e devolve o SteamID (17 digitos). `query` = dict de listas (parse_qs).
    Levanta LoginInvalido com uma mensagem curta, sem repetir o que veio na URL."""
    agora = time.time() if agora is None else agora
    p = {k: v[0] for k, v in query.items() if v}
    state = p.get("s", "")
    with _lock:
        criado = _pendentes.pop(state, None)   # uso unico: reenviar o mesmo retorno falha
    if criado is None or agora - criado > VALIDADE:
        raise LoginInvalido("O pedido de entrada expirou ou não foi feito por este Hunter. Tente de novo.")
    if p.get("openid.ns") != NS or p.get("openid.mode") != "id_res":
        raise LoginInvalido("A Steam não confirmou a entrada.")
    if p.get("openid.op_endpoint") != ENDPOINT or p.get("openid.return_to") != _retorno(base, state):
        raise LoginInvalido("Resposta que não veio da Steam para este Hunter.")
    m = RE_ID.match(p.get("openid.claimed_id", ""))
    if not m or p.get("openid.identity") != p.get("openid.claimed_id"):
        raise LoginInvalido("A Steam não devolveu um SteamID válido.")
    assinados = set((p.get("openid.signed") or "").split(","))
    if not {"claimed_id", "identity", "return_to", "response_nonce", "op_endpoint"} <= assinados:
        raise LoginInvalido("Resposta da Steam sem a assinatura esperada.")
    n = p.get("openid.response_nonce", "")
    mn = RE_NONCE.match(n)
    if not mn:
        raise LoginInvalido("Resposta da Steam sem nonce.")
    try:
        quando = calendar.timegm(time.strptime(mn.group(1), "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        raise LoginInvalido("Resposta da Steam com data inválida.")
    if abs(agora - quando) > VALIDADE:
        raise LoginInvalido("Resposta da Steam velha demais. Tente de novo.")
    with _lock:
        if n in _nonces:
            raise LoginInvalido("Essa resposta da Steam já foi usada.")
        _nonces[n] = agora
    try:
        ok = confirmar({k: v for k, v in p.items() if k.startswith("openid.")})
    except (urllib.error.URLError, OSError):
        raise LoginInvalido("Não consegui falar com a Steam para confirmar. Tente de novo.")
    if not ok:
        raise LoginInvalido("A Steam recusou a confirmação.")
    return m.group(1)
