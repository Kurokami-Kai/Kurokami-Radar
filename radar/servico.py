"""O ciclo que roda sozinho: coleta -> avalia -> notifica, no intervalo do config."""
import logging
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from . import analise, caminhos, coleta, config, progresso, relatorio
from .banco import Banco
from .notificador import Notificador


def criar_log(eco=False):
    caminhos.garantir()
    lg = logging.getLogger("radar")
    if not lg.handlers:
        lg.setLevel(logging.INFO)
        h = RotatingFileHandler(caminhos.ARQ_LOG, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%d/%m %H:%M:%S"))
        lg.addHandler(h)
        if eco:
            lg.addHandler(logging.StreamHandler())
    return lg.info


def _fim_iso(v):
    try:
        return int(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def candidatos_fim(b, alertas, cfg):
    """O que esta no carrinho ou "vale a pena" e tem data de fim conhecida (ITAD ou Steam)."""
    import json as _json
    try:
        with open(caminhos.ARQ_CARRINHO, encoding="utf-8") as f:
            carr = {int(i["appid"]) for i in _json.load(f) if i.get("appid")}
    except (OSError, ValueError):
        carr = set()
    alvo = {a["appid"]: a for a in alertas}
    out = []
    marc = {l.lower() for l in cfg["lojas"]}
    for a in carr | set(alvo):
        j = b.um("SELECT nome, preco_steam, desconto_steam, fim_desconto FROM jogo WHERE appid=?", a)
        if not j:
            continue
        ofs = [dict(r) for r in b.q("SELECT * FROM oferta_atual WHERE appid=? AND corte>0", a) if r["loja"].lower() in marc]
        melhor = min(ofs, key=lambda o: o["preco"]) if ofs else None
        fim = _fim_iso(melhor["expira"]) if melhor and melhor.get("expira") else None
        if fim is None and j["desconto_steam"]:
            fim = j["fim_desconto"]
            melhor = melhor or {"loja": "Steam", "preco": j["preco_steam"], "corte": j["desconto_steam"], "url": None}
        if fim and melhor:
            out.append({"appid": a, "nome": j["nome"], "preco": melhor["preco"], "corte": melhor["corte"],
                        "loja": melhor["loja"], "url": melhor.get("url"), "fim": fim, "carrinho": a in carr})
    return out


def ciclo(log=print, forcar=False, sem_limite=False):
    """Uma rodada. forcar+sem_limite = verificacao completa. Devolve (alertas, novos)."""
    cfg = config.carregar()
    b = Banco()
    log_ = log

    def log(msg):
        progresso.linha(msg)
        log_(msg)
    progresso.iniciar("completa" if (forcar and sem_limite) else "rapida")
    try:
        ofertas, gg, marcadas = coleta.atualizar(cfg, b, forcar=forcar, sem_limite=sem_limite, log=log)
        ctx = analise.Contexto(b, cfg)
        log("Avaliando ofertas e notificando")
        alertas = analise.avaliar(ctx, ofertas, gg, marcadas)
        notif = Notificador(b, cfg, log)
        novos = notif.processar(alertas)
        try:
            notif.terminando(candidatos_fim(b, alertas, cfg))
        except Exception as e:
            log("Aviso de fim de promocao falhou: %s" % e)
        from .banco import agora
        b.meta("ultimos_alertas", {"quando": agora(), "itens": alertas, "novos": [a["appid"] for a in novos]})
        b.commit()
        capas = {a["appid"]: (ctx.jogos.get(a["appid"]) or {}).get("capa") for a in alertas}
        relatorio.gerar(alertas, capas, {a["appid"] for a in novos})
        log("Ciclo ok: %d valem a pena, %d notificado(s)" % (len(alertas), len(novos)))
        if forcar and sem_limite:
            b.meta("ult_completa", __import__("radar.banco", fromlist=["agora"]).agora())
            b.commit()
        progresso.fim(True, "%d valem a pena, %d notificado(s)" % (len(alertas), len(novos)))
        return alertas, novos
    except Exception as e:
        progresso.fim(False, str(e))
        raise
    finally:
        b.con.close()


class Servico(threading.Thread):
    def __init__(self, log, ao_mudar=None):
        super().__init__(daemon=True)
        self.log, self.ao_mudar = log, ao_mudar or (lambda: None)
        self.acordar = threading.Event()
        self.parar = False
        self.proxima = datetime.now()
        self.estado = "iniciando"
        self.ultimo = None

    def _precisa_completa(self):
        """1a checagem e sempre completa; depois, a cada N dias (config verificacao_completa_dias)."""
        b = Banco()
        try:
            ult = b.meta("ult_completa")
        finally:
            b.con.close()
        if not ult:
            return True
        dias = config.carregar().get("verificacao_completa_dias", 7) or 0
        return bool(dias) and (datetime.now(timezone.utc) - datetime.fromisoformat(ult)).days >= dias

    def agora(self, completo=False):
        self.completo = completo or getattr(self, "completo", False)
        self.proxima = datetime.now()
        self.acordar.set()

    def run(self):
        falhas = 0
        while not self.parar:
            espera = (self.proxima - datetime.now()).total_seconds()
            if espera > 0:
                self.acordar.wait(min(espera, 30))  # acorda de 30 em 30s: sobrevive a suspensao do PC
                self.acordar.clear()
                continue
            self.estado = "verificando"
            self.ao_mudar()
            try:
                completo, self.completo = getattr(self, "completo", False), False
                completo = completo or self._precisa_completa()
                alertas, novos = ciclo(self.log, forcar=completo, sem_limite=completo)
                self.ultimo = (datetime.now(), len(alertas), len(novos))
                falhas = 0
                intervalo = config.carregar()["intervalos_minutos"]["itad"]
            except Exception as e:
                falhas += 1
                self.log("Erro no ciclo (%s). Detalhes:\n%s" % (e, traceback.format_exc()))
                intervalo = min(5 * 2 ** (falhas - 1), 60)  # sem internet etc.: tenta de novo em 5, 10, 20... min
            self.proxima = datetime.now() + timedelta(minutes=intervalo)
            self.estado = "ok" if not falhas else "erro"
            self.ao_mudar()
