"""O ciclo que roda sozinho: coleta -> avalia -> notifica, no intervalo do config.
Duas pistas (0.18.2): a RAPIDA (`ciclo`, de 15 em 15 min: precos, Steam inteira, avisos) e a LENTA (`ciclo_lento`, thread
propria: catalogo da Steam, biblioteca, historicos da ITAD), para o trabalho lento nunca atrasar a checagem de promocoes."""
import logging
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from . import analise, caminhos, coleta, config, credenciais, progresso, rede, relatorio
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
        ofs = [dict(r) for r in b.q("SELECT * FROM oferta_atual WHERE appid=? AND corte>0", a)
               if r["loja"].lower() in marc and (r["drm_steam"] or not cfg.get("somente_drm_steam"))]
        melhor = min(ofs, key=lambda o: o["preco"]) if ofs else None
        fim = _fim_iso(melhor["expira"]) if melhor and melhor.get("expira") else None
        if fim is None and j["desconto_steam"]:
            fim = j["fim_desconto"]
            melhor = melhor or {"loja": "Steam", "preco": j["preco_steam"], "corte": j["desconto_steam"], "url": None}
        if fim and melhor:
            out.append({"appid": a, "nome": j["nome"], "preco": melhor["preco"], "corte": melhor["corte"],
                        "loja": melhor["loja"], "url": melhor.get("url"), "fim": fim, "carrinho": a in carr})
    return out


def ciclo(log=print, forcar=False, sem_limite=False, steam_agora=False, faixa="tudo"):
    """Uma rodada. forcar+sem_limite = verificacao completa. Devolve (alertas, novos).
    faixa "rapida" e a do servico (o lento fica em `ciclo_lento`); "tudo" e a da linha de comando."""
    cfg = config.carregar()
    b = Banco()
    rede.usar_banco(b)   # nada de transacao aberta durante a rede (a outra pista e o painel gravam no mesmo banco)
    log_ = log

    def log(msg):
        progresso.linha(msg)
        log_(msg)
    progresso.iniciar("completa" if (forcar and sem_limite and faixa == "tudo") else "rapida")
    try:
        ofertas, gg, marcadas = coleta.atualizar(cfg, b, forcar=forcar, sem_limite=sem_limite, log=log, steam_agora=steam_agora,
                                                 faixa=faixa)
        ctx = analise.Contexto(b, cfg)
        log("Avaliando ofertas e notificando")
        alertas = analise.avaliar(ctx, ofertas, gg, marcadas)
        notif = Notificador(b, cfg, log)
        if faixa == "rapida" and not b.meta("linha_de_base") and not b.meta("hist_inicial") and credenciais.ler("itad") \
                and _espera_historico(b):
            # 1a vez: sem o historico (segundo plano) nao ha Selo, e a linha de base sairia vazia e viraria avalanche depois
            log("Primeira avaliacao: aguardando o historico das lojas (segundo plano) para nao avisar de tudo de uma vez")
            novos = []
        else:
            novos = notif.processar(alertas)
        try:
            notif.steam_inteira(ctx)
        except Exception as e:
            log("Avisos da Steam inteira falharam: %s" % e)
        try:
            notif.terminando(candidatos_fim(b, alertas, cfg))
        except Exception as e:
            log("Aviso de fim de promocao falhou: %s" % e)
        from .banco import agora
        b.meta("ultimos_alertas", {"quando": agora(), "itens": alertas, "novos": [a["appid"] for a in novos]})
        b.commit()
        capas = {a["appid"]: (ctx.jogos.get(a["appid"]) or {}).get("capa") for a in alertas}
        relatorio.gerar(alertas, capas, {a["appid"] for a in novos})
        from . import painel
        painel.invalidar_linhas()  # a vitrine e a aba Promocoes passam a ver a coleta nova
        from . import ofertas
        ofertas.aquecer()  # Ofertas e Biblioteca já montadas quando o painel abrir
        log("Ciclo ok: %d valem a pena, %d notificado(s)" % (len(alertas), len(novos)))
        if forcar and sem_limite and faixa == "tudo":   # na pista rapida quem marca e a lenta, ao terminar
            b.meta("ult_completa", __import__("radar.banco", fromlist=["agora"]).agora())
            b.commit()
        progresso.fim(True, "%d valem a pena, %d notificado(s)" % (len(alertas), len(novos)))
        return alertas, novos
    except Exception as e:
        progresso.fim(False, str(e))
        raise
    finally:
        rede.usar_banco(None)
        b.con.close()


def _espera_historico(b, horas=12):
    """Ainda vale esperar o historico da 1a instalacao? Teto de `horas` desde a 1a espera (nao fica sem aviso para sempre)."""
    ini = b.meta("espera_historico")
    if not ini:
        from .banco import agora
        b.meta("espera_historico", agora())
        b.commit()
        return True
    return (datetime.now(timezone.utc) - datetime.fromisoformat(ini)).total_seconds() < horas * 3600


def ciclo_lento(log=print, forcar=False):
    """Uma rodada da pista lenta (thread propria). forcar = a parte lenta da verificacao completa (sem orcamento de chamadas;
    ao terminar marca `ult_completa`). Devolve True se ainda ha o que fazer logo."""
    cfg = config.carregar()
    b = Banco()
    rede.usar_banco(b)
    feito = []
    modo = "completa" if forcar else "segundo plano"

    def log_(msg):
        if not feito:   # so aparece "segundo plano" no painel quando ha trabalho de verdade
            progresso.iniciar(modo)
        feito.append(1)
        progresso.linha(msg)
        log(msg)
    try:
        restante = coleta.atualizar_lenta(cfg, b, forcar=forcar, sem_limite=forcar, log=log_)
        from .banco import agora
        if forcar:
            b.meta("ult_completa", agora())
            b.commit()
        if feito:
            from . import ofertas, painel
            painel.invalidar_linhas()   # o catalogo e os historicos novos entram nas telas
            ofertas.aquecer()
        if feito:
            progresso.fim(True, "segundo plano")
        return restante
    except Exception as e:
        if feito:
            progresso.fim(False, str(e))
        raise
    finally:
        rede.usar_banco(None)
        b.con.close()


class Lenta(threading.Thread):
    """A pista lenta: repete `ciclo_lento` ate acabar o trabalho (de 3 em 3 min) e, sem trabalho, confere de 10 em 10 min
    (a pista rapida a acorda a cada rodada, para jogo novo na lista ter historico logo)."""

    def __init__(self, servico):
        super().__init__(daemon=True)
        self.s = servico
        self.acordar = threading.Event()
        self.forcar = False
        self.completa_ativa = False   # ha uma verificacao completa pedida ou em andamento (a rapida nao pede outra)
        self.ocupada = False

    def pedir_completa(self):
        self.completa_ativa = self.forcar = True
        self.acordar.set()

    def run(self):
        rede.marcar_lenta()
        falhas = 0
        while not self.s.parar:
            forcar, self.forcar = self.forcar, False
            self.acordar.clear()   # pedido que chegar durante a rodada deixa o evento ligado e a proxima comeca logo
            self.ocupada = True
            try:
                restante = ciclo_lento(self.s.log, forcar=forcar)
                falhas = 0
                espera = 180 if restante else 600
            except Exception as e:
                falhas += 1
                self.s.log("Erro no segundo plano (%s). Detalhes:\n%s" % (e, traceback.format_exc()))
                espera = min(300 * falhas, 1800)
            self.ocupada = False
            if forcar and not self.forcar:
                self.completa_ativa = False
            self.acordar.wait(espera)


class Servico(threading.Thread):
    def __init__(self, log, ao_mudar=None):
        super().__init__(daemon=True)
        self.log, self.ao_mudar = log, ao_mudar or (lambda: None)
        self.acordar = threading.Event()
        self.parar = False
        self.proxima = datetime.now()
        self.estado = "iniciando"
        self.ultimo = None
        self.lenta = Lenta(self)

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
        self.manual = True   # pedido pelo usuario: puxa a Steam inteira mesmo fora do intervalo
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
                manual, self.manual = getattr(self, "manual", False), False
                completo = completo or (self._precisa_completa() and not self.lenta.completa_ativa)
                if completo:
                    self.lenta.pedir_completa()   # a parte lenta da completa roda em segundo plano
                alertas, novos = ciclo(self.log, forcar=completo, sem_limite=completo, steam_agora=manual, faixa="rapida")
                if not self.lenta.is_alive():
                    self.lenta.start()   # 1a rodada rapida feita: as listas ja estao no banco e o pedido de completa ja valeu
                elif not self.lenta.ocupada:
                    self.lenta.acordar.set()   # jogo novo na lista ganha historico logo
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
