"""Decide QUAIS alertas viram notificacao:
- primeira vez: so registra o que ja esta em promocao (sem avalanche de avisos);
- depois: avisa jogo que entrou no menor historico, ou que caiu mais ainda;
- quando a promocao acaba, o jogo "rearma" e volta a avisar na proxima;
- horario de silencio guarda os avisos para depois; acima do limite, vira um resumo."""
import json
from datetime import datetime

from . import caminhos, notificar
from .banco import agora

ESQUEMA = """CREATE TABLE IF NOT EXISTS notificado(
  appid INTEGER PRIMARY KEY, loja TEXT, preco INTEGER, quando TEXT, ativo INTEGER DEFAULT 1)"""


def brl(c):
    return "Grátis" if c == 0 else "R$ %s" % ("%.2f" % (c / 100)).replace(".", ",")


def em_silencio(cfg, agora_local=None):
    s = (cfg.get("notificacoes") or {}).get("silencio") or {}
    if not s.get("ativo"):
        return False
    t = (agora_local or datetime.now()).strftime("%H:%M")
    de, ate = s.get("de", "23:00"), s.get("ate", "08:00")
    return (de <= t < ate) if de <= ate else (t >= de or t < ate)


class Notificador:
    def __init__(self, banco, cfg, log=print):
        self.b, self.cfg, self.log = banco, cfg, log
        self.b.con.execute(ESQUEMA)

    def _lista_url(self):
        from . import painel
        return painel.url() if painel.CONTROLE["servico"] else notificar._uri(caminhos.ARQ_RELATORIO)

    def processar(self, alertas):
        ncfg = self.cfg.get("notificacoes") or {}
        melhora = int(round((ncfg.get("melhora_minima_reais") or 0.5) * 100))
        ja = {r["appid"]: dict(r) for r in self.b.q("SELECT * FROM notificado")}
        mudos = {r["appid"] for r in self.b.q("SELECT appid FROM silenciado")}
        alertas = [a for a in alertas if a["appid"] not in mudos]
        atuais = {a["appid"]: a for a in alertas}

        # rearma quem saiu do menor historico / da promocao
        sairam = [a for a, n in ja.items() if n["ativo"] and a not in atuais]
        self.b.con.executemany("UPDATE notificado SET ativo=0 WHERE appid=?", [(a,) for a in sairam])

        novos = []
        for a in alertas:
            n = ja.get(a["appid"])
            if n is None or not n["ativo"] or a["preco"] <= n["preco"] - melhora:
                novos.append(a)
            self.b.con.execute(
                "INSERT INTO notificado VALUES(?,?,?,?,1) ON CONFLICT(appid) DO UPDATE SET ativo=1, "
                "preco=CASE WHEN excluded.preco < notificado.preco OR notificado.ativo=0 THEN excluded.preco ELSE notificado.preco END, "
                "loja=excluded.loja, quando=CASE WHEN excluded.preco < notificado.preco OR notificado.ativo=0 THEN excluded.quando ELSE notificado.quando END",
                (a["appid"], a["loja"], a["preco"], agora()))

        if not self.b.meta("linha_de_base"):
            self.b.meta("linha_de_base", agora())
            self.b.commit()
            notificar.mostrar("Kurokami Radar ativo",
                              "%d jogos da sua lista já estão no menor histórico.\nDaqui pra frente você recebe só as novidades." % len(alertas),
                              clique=self._lista_url(), botoes=[("Ver lista", self._lista_url())])
            self.log("Linha de base: %d alertas atuais registrados sem notificar" % len(alertas))
            return []

        if self.b.meta("pausado"):
            self.b.commit()
            if novos:
                self.log("Pausado: %d novidade(s) sem notificar" % len(novos))
            return []

        if em_silencio(self.cfg):
            pend = {p["appid"]: p for p in (self.b.meta("pendentes") or [])}
            for a in novos:
                pend[a["appid"]] = a
            self.b.meta("pendentes", list(pend.values()))
            self.b.commit()
            if novos:
                self.log("Horario de silencio: %d aviso(s) guardado(s)" % len(novos))
            return []
        pend = self.b.meta("pendentes") or []
        if pend:  # entrega o que ficou guardado, se ainda estiver valendo
            vistos = {a["appid"] for a in novos}
            novos += [p for p in pend if p["appid"] in atuais and p["appid"] not in vistos]
            self.b.meta("pendentes", [])

        if not ncfg.get("ativas", True) or not novos:
            self.b.commit()
            return []

        novos.sort(key=lambda a: -(a.get("score") or 0))
        limite = max(1, int(ncfg.get("max_por_rodada") or 5))
        for a in novos[:limite]:
            self._enviar(a)
        if len(novos) > limite:
            resto = len(novos) - limite
            notificar.mostrar("+%d oferta%s no menor histórico" % (resto, "s" if resto > 1 else ""),
                              ", ".join(a["nome"] for a in novos[limite:limite + 4]) + ("…" if resto > 4 else ""),
                              clique=self._lista_url(), botoes=[("Ver lista", self._lista_url())])
        self.b.con.executemany("INSERT INTO alerta(appid, loja, preco, motivo, quando, enviado) VALUES(?,?,?,?,?,1)",
                               [(a["appid"], a["loja"], a["preco"], a["motivo"], agora()) for a in novos])
        self.b.commit()
        self.log("Notificados: %d" % len(novos))
        return novos

    def _enviar(self, a):
        j = self.b.um("SELECT capa FROM jogo WHERE appid=?", a["appid"])
        img = notificar.capa(a["appid"], j["capa"] if j else None)
        steam = "https://store.steampowered.com/app/%d/" % a["appid"]
        oferta = a.get("url") or steam
        desc = (" · -%d%%" % a["corte"]) if a.get("corte") else ""
        linha1 = "%s%s na %s" % (brl(a["preco"]), desc, a["loja"])
        linha2 = a["motivo"][0].upper() + a["motivo"][1:]
        if a.get("score"):
            linha2 += " · score %d" % round(a["score"])
        rodape = ("também: " + ", ".join(a["outras"])) if a.get("outras") else None
        botoes = [("Abrir oferta", oferta), ("Não avisar mais", self._acao("silenciar", a["appid"]))]
        from .analise import NOME_RARIDADE
        rar = a.get("raridade")
        if a.get("selo"):
            titulo = "SELO KUROKAMI · %s" % a["nome"]
        elif rar in ("ultrarraro", "lendario"):
            titulo = "%s · %s" % (NOME_RARIDADE[rar].upper(), a["nome"])
        else:
            titulo = a["nome"]
        notificar.mostrar(titulo, linha1 + "\n" + linha2, clique=oferta, botoes=botoes, imagem=img, rodape=rodape)

    def _acao(self, acao, appid):
        from . import painel
        return "%s/acao?%s=%d" % (painel.url(), acao, appid)

    def terminando(self, candidatos):
        """candidatos: [{"appid","nome","preco","corte","loja","fim"(epoch)}]. Avisa 1x por promocao."""
        import time
        horas = (self.cfg.get("notificacoes") or {}).get("termina_em_breve_horas", 24)
        if not horas or self.b.meta("pausado") or em_silencio(self.cfg):
            return []
        avisados = self.b.meta("avisos_fim") or {}
        agora_ = time.time()
        enviados = []
        mudos = {r["appid"] for r in self.b.q("SELECT appid FROM silenciado")}
        for c in candidatos:
            fim = c.get("fim")
            if not fim or c["appid"] in mudos or not (agora_ < fim <= agora_ + horas * 3600):
                continue
            if avisados.get(str(c["appid"])) == fim:
                continue
            avisados[str(c["appid"])] = fim
            h = max(1, round((fim - agora_) / 3600))
            j = self.b.um("SELECT capa FROM jogo WHERE appid=?", c["appid"])
            img = notificar.capa(c["appid"], j["capa"] if j else None)
            steam = "https://store.steampowered.com/app/%d/" % c["appid"]
            notificar.mostrar("Termina em %dh: %s" % (h, c["nome"]),
                              "%s%s na %s\n%s" % (brl(c["preco"]), (" · -%d%%" % c["corte"]) if c.get("corte") else "", c["loja"],
                                                   "está no seu carrinho" if c.get("carrinho") else "vale a pena pelos seus filtros"),
                              clique=c.get("url") or steam, botoes=[("Abrir oferta", c.get("url") or steam)], imagem=img)
            enviados.append(c)
        # limpa o que ja passou
        self.b.meta("avisos_fim", {k: v for k, v in avisados.items() if v > agora_ - 86400})
        self.b.commit()
        if enviados:
            self.log("Avisos de fim de promocao: %d" % len(enviados))
        return enviados
