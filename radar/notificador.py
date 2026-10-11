"""Decide QUAIS alertas viram notificacao:
- primeira vez: so registra o que ja esta em promocao (sem avalanche de avisos);
- depois: avisa jogo que entrou num tipo de preco ligado (Selo, novo recorde, igual, menor em 2 anos), ou que caiu mais ainda;
- ligar um tipo nas Configuracoes nao dispara em massa: quem ja estava assim entra sem aviso e sai um resumo;
- quando a promocao acaba, o jogo "rearma" e volta a avisar na proxima;
- horario de silencio guarda os avisos para depois; acima do limite, vira um resumo."""
import json
from datetime import datetime, timedelta, timezone

from . import caminhos, notificar, telegram
from .banco import agora

ESQUEMA = """CREATE TABLE IF NOT EXISTS notificado(
  appid INTEGER PRIMARY KEY, loja TEXT, preco INTEGER, quando TEXT, ativo INTEGER DEFAULT 1)"""


ESQUEMA_PROMO = "CREATE TABLE IF NOT EXISTS notificado_promo(appid INTEGER PRIMARY KEY, entrou TEXT)"
# texto de cada tipo de preco na Steam inteira (as mesmas frases da lista; a aba Notificacoes as reconhece pelo comeco)
MOTIVO_PROMO = {"novo": "menor preço já registrado", "igual": "mesmo preço do menor já registrado", "24m": "menor preço em 2 anos"}
HORAS_ENTROU = 36   # so avisa quem entrou na Steam inteira nas ultimas 36 h (o Selo chega com o historico, aos poucos)


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
        self.b.con.execute(ESQUEMA_PROMO)

    def _avisar(self, titulo, texto, clique=None, botoes=(), imagem=None, rodape=None, foto=None):
        """Um aviso, nos dois canais: toast do Windows (se ativo) e Telegram (se ligado)."""
        if (self.cfg.get("notificacoes") or {}).get("ativas", True):
            notificar.mostrar(titulo, texto, clique=clique, botoes=botoes, imagem=imagem, rodape=rodape)
        if telegram.ligado(self.cfg):
            telegram.enviar(self.cfg, titulo, texto + ("\n" + rodape if rodape else ""), botoes=botoes, foto=foto)

    def _lista_url(self):
        from . import painel
        return painel.url() if painel.CONTROLE["servico"] else notificar._uri(caminhos.ARQ_RELATORIO)

    def _vitrine_url(self):
        from . import painel
        return painel.url() + "#vale" if painel.CONTROLE["servico"] else self._lista_url()

    def processar(self, alertas):
        ncfg = self.cfg.get("notificacoes") or {}
        melhora = int(round((ncfg.get("melhora_minima_reais") or 0.5) * 100))
        ja = {r["appid"]: dict(r) for r in self.b.q("SELECT * FROM notificado")}
        mudos = {r["appid"] for r in self.b.q("SELECT appid FROM silenciado")}
        alertas = [a for a in alertas if a["appid"] not in mudos]
        atuais = {a["appid"]: a for a in alertas}

        # rearma quem deixou de valer a pena / saiu da promocao
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

        from .analise import NOME_TIPO, chave_aviso, tipos_ligados
        lig = tipos_ligados(self.cfg.get("alerta"))
        ant = self.b.meta("tipos_ligados")
        self.b.meta("tipos_ligados", lig)
        if not self.b.meta("linha_de_base"):
            self.b.meta("linha_de_base", agora())
            self.b.commit()
            notificar.mostrar("Kurokami Hunter ativo",
                              "%d jogos da sua lista já valem a pena agora.\nDaqui pra frente você recebe só as novidades." % len(alertas),
                              clique=self._lista_url(), botoes=[("Ver lista", self._lista_url())])
            self.log("Linha de base: %d alertas atuais registrados sem notificar" % len(alertas))
            return []

        # tipo que acabou de ser ligado: quem ja estava assim (e so avisaria por ele) entra sem toast; sai 1 resumo.
        # Sem meta.tipos_ligados (1a rodada da 0.15) nada e "recem-ligado".
        ligou = [t for t in lig if ant is not None and t not in ant]
        resumos = []
        if ligou:
            so_por = [a for a in novos if a.get("avisa_por") and set(a["avisa_por"]) <= set(ligou)]
            ids = {a["appid"] for a in so_por}
            novos = [a for a in novos if a["appid"] not in ids]
            for t in ligou:
                n = sum(1 for a in so_por if t in a["avisa_por"])
                if n:
                    resumos.append((t, n))
                self.log("%s ligado: %d jogo(s) ja estavam assim, registrados sem aviso" % (NOME_TIPO[t], n))

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

        for t, n in resumos:
            self._avisar("%s ligado" % NOME_TIPO[t],
                         "%d jogo%s já %s assim agora. Você vai receber só os próximos." % (
                             n, "s" if n > 1 else "", "estão" if n > 1 else "está"),
                         clique=self._vitrine_url(), botoes=[("Ver", self._vitrine_url())])
        if not (ncfg.get("ativas", True) or telegram.ligado(self.cfg)) or not novos:
            self.b.commit()
            return []

        novos.sort(key=chave_aviso)  # selo, novo, igual, 24m; maior corte primeiro
        limite = max(1, int(ncfg.get("max_por_rodada") or 5))
        for a in novos[:limite]:
            self._enviar(a)
        if len(novos) > limite:
            resto = len(novos) - limite
            self._avisar("+%d oferta%s que vale%s a pena" % (resto, "s" if resto > 1 else "", "m" if resto > 1 else ""),
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
        from .analise import texto_outras
        motivo = a["motivo"]
        if motivo.startswith("Selo Kurokami: "):
            motivo = motivo[len("Selo Kurokami: "):]  # o titulo ja diz SELO KUROKAMI
        linha2 = motivo[0].upper() + motivo[1:]
        rodape = texto_outras(a) or None
        botoes = [("Abrir oferta", oferta), ("Não avisar mais", self._acao("silenciar", a["appid"]))]
        from .analise import NOME_TIPO
        t = a.get("tipo_oferta")  # o titulo nunca usa raridade (spec 04)
        if t == "selo":
            titulo = "SELO KUROKAMI · %s" % a["nome"]
        elif t in NOME_TIPO:
            titulo = "%s · %s" % (NOME_TIPO[t], a["nome"])
        else:
            titulo = a["nome"]
        self._avisar(titulo, linha1 + "\n" + linha2, clique=oferta, botoes=botoes, imagem=img, rodape=rodape,
                     foto=j["capa"] if j else None)

    def steam_inteira(self, ctx):
        """Avisa jogos da Steam inteira FORA da sua lista (a lista tem o caminho de `processar`): so os tipos ligados em
        alerta.tipos (padrao: Selo), jogos (sem DLC, sem +18) com analises_minimas, que entraram em promocao nas ultimas
        36 h e que voce nao tem, nao ignora nem silenciou. Uma vez por promocao; acima de max_por_rodada vira um resumo."""
        from . import conta_steam
        from .analise import NOME_TIPO, avisa_por, ordem_tipo, tipo_oferta
        sc = self.cfg.get("steam_inteira_avisos") or {}
        if not (self.cfg.get("steam_inteira", True) and sc.get("ativo", True)) or not self.b.meta("linha_de_base"):
            return []
        if self.b.meta("pausado") or em_silencio(self.cfg):
            return []
        desde = (datetime.now(timezone.utc) - timedelta(hours=HORAS_ENTROU)).replace(microsecond=0).isoformat()
        minimo = int(sc.get("analises_minimas") or 0)
        ja = {r["appid"]: r["entrou"] for r in self.b.q("SELECT appid, entrou FROM notificado_promo")}
        fora = set(ctx.jogos) | {r["appid"] for r in self.b.q("SELECT appid FROM silenciado")}             | {r["appid"] for r in self.b.q("SELECT appid FROM tenho_manual")} | conta_steam.relacao(self.cfg)["ignorados"]
        achados = []
        for r in self.b.q("SELECT * FROM steam_promo WHERE tipo='jogo' AND COALESCE(adulto,0)=0 AND entrou>=? AND rcount>=?",
                          desde, minimo):
            if r["appid"] in fora or ja.get(r["appid"]) == r["entrou"] or not r["aval"]:
                continue
            try:
                aval = json.loads(r["aval"])
            except ValueError:
                continue
            if aval.get("provisorio"):   # so a marca da ITAD, sem historico: espera a avaliacao de verdade
                continue
            tipos = avisa_por(aval.get("tipos") or [], r["corte"], self.cfg.get("alerta"))
            if not tipos:
                continue
            t = tipo_oferta(tipos)
            if t == "selo":
                motivo = "Selo Kurokami: " + (aval.get("selo_motivo") or "o menor preço em muito tempo")
            else:
                motivo = MOTIVO_PROMO[t]
            achados.append(dict(r, tipo_oferta=t, motivo=motivo))
        # quem saiu da promocao deixa de ocupar a tabela
        self.b.con.execute("DELETE FROM notificado_promo WHERE appid NOT IN (SELECT appid FROM steam_promo)")
        if not achados:
            self.b.commit()
            return []
        achados.sort(key=lambda a: (ordem_tipo(a["tipo_oferta"]), -(a["rcount"] or 0)))
        limite = max(1, int(sc.get("max_por_rodada") or 3))
        for a in achados:
            self.b.con.execute("INSERT OR REPLACE INTO notificado_promo VALUES(?,?)", (a["appid"], a["entrou"]))
        if self.cfg.get("notificacoes", {}).get("ativas", True) or telegram.ligado(self.cfg):
            for a in achados[:limite]:
                steam = "https://store.steampowered.com/app/%d/" % a["appid"]
                nome = a["nome"]
                titulo = ("SELO KUROKAMI · %s" if a["tipo_oferta"] == "selo" else NOME_TIPO[a["tipo_oferta"]] + " · %s") % nome
                motivo = a["motivo"][len("Selo Kurokami: "):] if a["tipo_oferta"] == "selo" else a["motivo"]
                self._avisar(titulo, "%s · -%d%% na Steam\n%s" % (brl(a["preco"]), a["corte"], motivo[0].upper() + motivo[1:]),
                             clique=steam, botoes=[("Abrir oferta", steam), ("Não avisar mais", self._acao("silenciar", a["appid"]))],
                             imagem=notificar.capa(a["appid"], a["capa"]), foto=a["capa"],
                             rodape="%s · %d análises" % (a["rotulo"] or "Sem rótulo", a["rcount"] or 0) if a["rcount"] else None)
            if len(achados) > limite:
                resto = achados[limite:]
                self._avisar("+%d promoç%s da Steam inteira" % (len(resto), "ões" if len(resto) > 1 else "ão"),
                             ", ".join(a["nome"] for a in resto[:4]) + ("…" if len(resto) > 4 else ""),
                             clique=self._lista_url(), botoes=[("Ver lista", self._lista_url())])
        self.b.con.executemany("INSERT INTO alerta(appid, loja, preco, motivo, quando, enviado) VALUES(?,?,?,?,?,1)",
                               [(a["appid"], "Steam", a["preco"], a["motivo"], agora()) for a in achados])
        self.b.commit()
        self.log("Steam inteira: %d aviso(s) de jogos fora da sua lista" % len(achados))
        return achados

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
            enviados.append(c)
        # mesmo limite dos alertas: carrinho primeiro, depois o que acaba antes; o resto vira um resumo
        enviados.sort(key=lambda c: (not c.get("carrinho"), c["fim"]))
        limite = max(1, int((self.cfg.get("notificacoes") or {}).get("max_por_rodada") or 5))
        for c in enviados[:limite]:
            fim = c["fim"]
            h = max(1, round((fim - agora_) / 3600))
            j = self.b.um("SELECT capa FROM jogo WHERE appid=?", c["appid"])
            img = notificar.capa(c["appid"], j["capa"] if j else None)
            steam = "https://store.steampowered.com/app/%d/" % c["appid"]
            self._avisar("Termina em %dh: %s" % (h, c["nome"]),
                         "%s%s na %s\n%s" % (brl(c["preco"]), (" · -%d%%" % c["corte"]) if c.get("corte") else "", c["loja"],
                                              "está no seu carrinho" if c.get("carrinho") else "vale a pena pelos seus filtros"),
                         clique=c.get("url") or steam, botoes=[("Abrir oferta", c.get("url") or steam)], imagem=img,
                         foto=j["capa"] if j else None)
        if len(enviados) > limite:
            resto = enviados[limite:]
            self._avisar("+%d terminando em breve" % len(resto),
                         ", ".join(c["nome"] for c in resto[:4]) + ("…" if len(resto) > 4 else ""),
                         clique=self._lista_url(), botoes=[("Ver lista", self._lista_url())])
        # limpa o que ja passou
        self.b.meta("avisos_fim", {k: v for k, v in avisados.items() if v > agora_ - 86400})
        self.b.commit()
        if enviados:
            self.log("Avisos de fim de promocao: %d" % len(enviados))
        return enviados
