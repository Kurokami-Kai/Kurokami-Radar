"""HTTP com JSON, backoff em 429/5xx e ritmo adaptativo (mesma logica do KurokamiPrecos)."""
import gzip
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


RITMO = {"steam": Ritmo(0.5), "itad": Ritmo(0.35), "gg": Ritmo(1.0), "loja": Ritmo(1.6, piso=1.5),
         # pista lenta (0.18.2): historico e biblioteca na ITAD sem estourar a cota (~100 chamadas em 5 min, medido) que a
         # pista rapida (precos de 15 em 15 min) tambem usa
         "itad_lento": Ritmo(4.0, piso=4.0, teto=10.0)}

# Duas pistas (0.18.2): a rapida (precos, Steam inteira, avisos) roda de 15 em 15 min; a lenta (catalogo, biblioteca, historicos)
# roda noutra thread. A lenta usa o Ritmo "itad_lento" e espera enquanto a rapida esta usando a ITAD.
_lenta = threading.local()
URGENTE = threading.Event()


def marcar_lenta():
    """Chamado uma vez pela thread da pista lenta."""
    _lenta.on = True


def usar_banco(banco):
    """A thread que chama promete nao segurar transacao do `banco` enquanto espera a rede: `http_json` confirma antes de cada
    tentativa. Sem isso, a pista lenta (ou a rapida) segurava o lock de escrita do SQLite durante a espera e a outra
    estourava o timeout de 30 s ("database is locked"). None desliga."""
    _lenta.banco = banco


def _soltar():
    b = getattr(_lenta, "banco", None)
    if b is not None:
        try:
            b.commit()
        except Exception:   # se nao deu (banco ocupado), a proxima escrita da propria thread levanta o erro de verdade
            pass


def e_lenta():
    return getattr(_lenta, "on", False)


class urgente:
    """`with rede.urgente():` na pista rapida, em volta do que usa a ITAD: a lenta espera ate acabar."""
    def __enter__(self):
        URGENTE.set()

    def __exit__(self, *_):
        URGENTE.clear()


def http_json(url, corpo=None, metodo=None, ritmo=None, tentativas=4, timeout=45, form=None):
    cab = {"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"}
    dados = None
    if form is not None:
        dados = urllib.parse.urlencode(form).encode()
        cab["Content-Type"] = "application/x-www-form-urlencoded"
        metodo = metodo or "POST"
    elif corpo is not None:
        dados = json.dumps(corpo).encode()
        cab["Content-Type"] = "application/json"
    espera = 2.0
    lenta = e_lenta() and ritmo is RITMO["itad"]
    if lenta:
        ritmo = RITMO["itad_lento"]
    for n in range(1, tentativas + 1):
        _soltar()
        if lenta:
            while URGENTE.is_set():   # a pista rapida tem a vez na ITAD
                time.sleep(1)
        if ritmo:
            ritmo.aguardar()
        req = urllib.request.Request(url, data=dados, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                bruto = r.read()
                if (r.headers.get("Content-Encoding") or "").lower() in ("gzip", "x-gzip"):   # Steam Query: 1,5 MB -> 150 KB por pagina
                    bruto = gzip.decompress(bruto)
                txt = bruto.decode("utf-8", "replace")
            if ritmo:
                ritmo.ok()
            return json.loads(txt) if txt.strip() else None
        except urllib.error.HTTPError as e:
            try:
                bruto_erro = e.read()
                if (e.headers.get("Content-Encoding") or "").lower() in ("gzip", "x-gzip"):
                    bruto_erro = gzip.decompress(bruto_erro)
                e.corpo = bruto_erro.decode("utf-8", "replace")[:300].strip()
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
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, EOFError, OSError):   # OSError: gzip cortado/invalido
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
