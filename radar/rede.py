"""HTTP com JSON, backoff em 429/5xx e ritmo adaptativo (mesma logica do KurokamiPrecos)."""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "KurokamiRadar/0.1 (uso pessoal)"


class Ritmo:
    def __init__(self, intervalo=0.4, piso=0.35, teto=5.0):
        self.lock = threading.Lock()
        self.intervalo, self.piso, self.teto = max(intervalo, piso), piso, teto
        self.livre_em = 0.0

    def aguardar(self):
        with self.lock:
            inicio = max(time.monotonic(), self.livre_em)
            self.livre_em = inicio + self.intervalo
        atraso = inicio - time.monotonic()
        if atraso > 0:
            time.sleep(atraso)

    def freio(self, pausa):
        with self.lock:
            self.intervalo = min(max(self.intervalo * 1.6, self.piso), self.teto)
            self.livre_em = max(self.livre_em, time.monotonic() + min(pausa, 60))

    def ok(self):
        with self.lock:
            self.intervalo = max(self.intervalo * 0.9, self.piso)


RITMO = {"steam": Ritmo(0.5), "itad": Ritmo(0.35), "gg": Ritmo(1.0), "loja": Ritmo(1.6, piso=1.5)}


def http_json(url, corpo=None, metodo=None, ritmo=None, tentativas=4, timeout=45, form=None):
    cab = {"User-Agent": UA, "Accept": "application/json"}
    dados = None
    if form is not None:
        dados = urllib.parse.urlencode(form).encode()
        cab["Content-Type"] = "application/x-www-form-urlencoded"
        metodo = metodo or "POST"
    elif corpo is not None:
        dados = json.dumps(corpo).encode()
        cab["Content-Type"] = "application/json"
    espera = 2.0
    for n in range(1, tentativas + 1):
        if ritmo:
            ritmo.aguardar()
        req = urllib.request.Request(url, data=dados, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode("utf-8", "replace")
            if ritmo:
                ritmo.ok()
            return json.loads(txt) if txt.strip() else None
        except urllib.error.HTTPError as e:
            try:
                e.corpo = e.read().decode("utf-8", "replace")[:300].strip()
            except Exception:
                e.corpo = ""
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                pausa = float(ra) if ra and ra.isdigit() else espera
                if ritmo:
                    ritmo.freio(pausa)
                else:
                    time.sleep(pausa)
                espera = min(espera * 2, 120)
                continue
            if 500 <= e.code < 600 and n < tentativas:
                time.sleep(espera)
                espera *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if n < tentativas:
                time.sleep(espera)
                espera *= 2
                continue
            raise
    raise RuntimeError("Falha ao acessar %s" % url.split("?")[0])


def servico_steam(url, entrada, chave=None, ritmo=None):
    """Endpoints 'Service' da Steam: GET com input_json; POST so se o GET der 405."""
    params = {"input_json": json.dumps(entrada, separators=(",", ":"))}
    if chave:
        params["key"] = chave
    try:
        return http_json(url + "?" + urllib.parse.urlencode(params), ritmo=ritmo)
    except urllib.error.HTTPError as e:
        if e.code != 405:
            raise
    return http_json(url, form=params, ritmo=ritmo)


def explicar(e):
    """Mensagem curta de um erro HTTP, com o motivo que o servidor mandou."""
    corpo = getattr(e, "corpo", "") or ""
    return ("HTTP %s%s" % (getattr(e, "code", "?"), (" - " + corpo) if corpo else "")) if hasattr(e, "code") else str(e)


def lotes(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def centavos(v):
    """Centavos como a Steam manda ("413" ou 413)."""
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def de_reais(v):
    """Valor decimal (ITAD amount, GG.deals "9.99" ou "10") para centavos."""
    if v is None or v == "":
        return None
    try:
        return int(round(float(str(v).replace(",", ".")) * 100))
    except (TypeError, ValueError):
        return None
