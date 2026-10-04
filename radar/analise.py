"""Score, custo completo, bundles com desconto do que voce ja tem e regras de alerta."""
import json

from . import dlc as dlcmod
from .config import modo_do_jogo

LOJA_COMPLETO = "Completo (Steam)"
LOJA_GG_OFICIAL = "GG.deals oficial"
LOJA_GG_KEYSHOP = "GG.deals keyshop"


JANELAS = [(0, "sempre", "menor preço de todos os tempos"), (365, "1a", "menor preço em 1 ano"),
           (270, "9m", "menor preço em 9 meses"), (180, "6m", "menor preço em 6 meses"), (90, "3m", "menor preço em 3 meses")]
ORDEM_TAG = {"sempre": 5, "1a": 4, "9m": 3, "6m": 2, "3m": 1, "perto": 0}


def etiqueta(preco, cheio, pisos, cfg_alerta, flag=None):
    """Qual o 'tamanho' do piso que este preco atinge. Devolve (tag, texto, acima_do_menor_de_sempre).
    tag: sempre | 1a | 9m | 6m | 3m | perto | None"""
    if preco is None or not pisos:
        return None, None, None
    tol = 1 + (cfg_alerta.get("tolerancia_pct") or 0) / 100
    # centavos de diferenca (cambio, arredondamento) contam como "igual"
    bate = lambda piso: piso is not None and preco <= piso * tol + max(10, piso * 0.01)
    sempre = pisos.get(0)
    acima = (preco - sempre) if sempre is not None else None
    # so vale dizer "menor em 1 ano" se ha pelo menos 1 ano de historico (jogo novo/recem-adicionado)
    span = pisos.get("dias")
    span = 10**6 if span is None else span
    if flag in ("H", "N") or (bate(sempre) and span >= 365):
        return "sempre", ("novo " if flag == "N" else "") + "menor preço de todos os tempos", acima
    for dias, tag, texto in JANELAS[1:]:
        if span >= dias and bate(pisos.get(dias)):
            return tag, texto, acima
    pe = cfg_alerta.get("perto") or {}
    if pe.get("ativo", True) and sempre is not None and cheio:
        limite = max((pe.get("reais") or 0) * 100, (pe.get("pct_do_cheio") or 0) / 100 * cheio)
        if acima <= limite:
            return "perto", "perto do menor de sempre (%s acima)" % _brl(acima), acima
    return None, None, acima


RARIDADES = ["comum", "incomum", "raro", "ultrarraro", "lendario"]
NOME_RARIDADE = {"comum": "Comum", "incomum": "Incomum", "raro": "Raro", "ultrarraro": "Ultrarraro", "lendario": "Lendário"}


DIA = 86400.0
PESO_RARIDADE = {"comum": 0.4, "incomum": 0.6, "raro": 0.8, "ultrarraro": 0.9, "lendario": 1.0}
TOL_NIVEL = 5            # pontos de corte: 75% conta como "mesmo nivel" quando hoje e 80%
JANELA_RARIDADE = 730    # dias (24 meses)


def _ts(q):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(q).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _iso(t):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, timezone.utc).replace(microsecond=0).isoformat() if t is not None else None


def _igual(preco, ref):
    """Centavos de diferenca (<= R$ 0,10 ou 1%) contam como igual."""
    return preco <= ref + max(10, ref * 0.01)


def _metade(preco, recorde):
    """Preco pela metade do recorde anterior, com a mesma folga de centavos do "igual" (R$ 0,10 ou 1% da metade).
    Ex.: WRC 7 a R$ 2,39 com recorde de R$ 4,74 (metade R$ 2,37) conta como metade."""
    return _igual(preco, recorde * 0.5)


def linha_do_tempo(linhas, agora_=None):
    """Junta o historico das lojas marcadas numa linha so: [(ini, fim, menor_preco, corte_do_menor, maior_corte)].
    Cada registro vale ate o proximo da mesma loja; promocao sem fim registrado vence em 45 dias;
    brindes (R$ 0) ficam de fora. Trechos sem nenhuma loja ativa tem menor_preco None."""
    import time
    agora_ = agora_ or time.time()
    VALIDADE_PROMO = 45 * DIA
    por_loja = {}
    for r in linhas:
        if not r["preco"]:
            continue
        t = _ts(r["quando"])
        if t is None or t > agora_:
            continue
        corte = (r["corte"] if "corte" in r.keys() else 0) or 0
        por_loja.setdefault(r["loja"], []).append((t, r["preco"], corte))
    # eventos: (tempo, tipo 0=sai/1=entra, loja, (preco, corte), id do registro)
    eventos = []
    for loja, regs in por_loja.items():
        regs.sort()
        for k, (t, p, c) in enumerate(regs):
            fim = regs[k + 1][0] if k + 1 < len(regs) else agora_
            if c > 0:
                fim = min(fim, t + VALIDADE_PROMO)
            if fim > t:
                eventos.append((t, 1, loja, (p, c), (loja, k)))
                eventos.append((fim, 0, loja, (p, c), (loja, k)))
    if not eventos:
        return []
    eventos.sort(key=lambda e: (e[0], e[1]))
    ativos, segs = {}, []
    for i, (t, tipo, loja, pc, rid) in enumerate(eventos):
        if tipo == 1:
            ativos[loja] = (pc, rid)
        elif loja in ativos and ativos[loja][1] == rid:
            del ativos[loja]
        z = eventos[i + 1][0] if i + 1 < len(eventos) else agora_
        if z <= t:
            continue
        if ativos:
            p, c = min(v[0] for v in ativos.values())
            segs.append((t, z, p, c, max(v[0][1] for v in ativos.values())))
        else:
            segs.append((t, z, None, 0, 0))
    # junta trechos vizinhos iguais
    out = []
    for s in segs:
        if out and out[-1][2:] == s[2:] and out[-1][1] == s[0]:
            out[-1] = (out[-1][0], s[1]) + s[2:]
        else:
            out.append(s)
    while out and out[0][2] is None:
        out.pop(0)
    return out


def episodios(segs, folga=DIA):
    """Promocoes como episodios: [(ini, fim, maior_corte)]. Um intervalo sem desconto menor que `folga`
    (uma loja acabou, outra comecou no mesmo dia) nao separa episodios."""
    eps = []
    for ini, fim, _p, _c, mc in segs:
        if mc <= 0:
            continue
        if eps and ini - eps[-1][1] < folga:
            eps[-1] = (eps[-1][0], fim, max(eps[-1][2], mc))
        else:
            eps.append((ini, fim, mc))
    return eps


def analisar(linhas, preco, corte, agora_=None, cfg_alerta=None):
    """Raridade v2 (frequencia do corte), piso (eixo 2), pilula de piso (reais) e Selo Kurokami.
    Devolve dict com: nivel, texto, por_ano, eps_nivel, ultima, corte_max, meses, curto, inicio,
    no_piso, selo, selo_motivo, piso_tipo, piso_ref, score, anteriores. nivel/piso_tipo sao None se nao ha promocao.
    Selo Kurokami = "o menor preco em muito tempo": Recorde raro (o recorde anterior tem 1,5 ano ou mais, ou o
    preco caiu pela metade) com >= 1 promocao anterior e corte >= alerta.selo_corte_minimo.
    A raridade (nivel) continua calculada, mas so alimenta a coluna "Costuma voltar" (costuma_voltar)."""
    import time
    agora_ = agora_ or time.time()
    segs = linha_do_tempo(linhas, agora_)
    corte = corte or 0
    out = {"nivel": None, "texto": None, "por_ano": None, "eps_nivel": 0, "ultima": None, "corte_max": corte,
           "meses": 0, "curto": True, "inicio": None, "no_piso": False, "selo": False, "selo_motivo": None,
           "piso_tipo": None, "piso_ref": None, "score": 0, "anteriores": 0}
    if not segs:
        if corte > 0:
            out.update(nivel="comum", texto="sem histórico nas lojas marcadas", score=_score_v2(corte, "comum", False))
        return out
    t0 = segs[0][0]
    dias_hist = (agora_ - t0) / DIA
    out["meses"] = int(dias_hist // 30.4)
    out["curto"] = dias_hist < 182
    eps = episodios(segs)
    # episodio atual: o ultimo, se ainda esta valendo
    atual = eps[-1] if eps and eps[-1][1] >= agora_ - 1 else None
    anteriores = eps[:-1] if atual else eps
    if atual:
        out["inicio"] = _iso(atual[0])
    out["anteriores"] = len(anteriores)
    corte_max = max([e[2] for e in eps] + [corte])
    out["corte_max"] = corte_max

    # ---- pilula de piso (reais): compara com o que havia ANTES do episodio de preco atual
    if preco is not None and corte > 0:
        ini_preco = agora_
        for s in reversed(segs):
            if s[2] is not None and _igual(s[2], preco):
                ini_preco = s[0]
            else:
                break
        antes = [s for s in segs if s[1] <= ini_preco and s[2] is not None]
        if antes:
            rec = min(antes, key=lambda s: (s[2], -s[0]))
            recorde = rec[2]
            ultima_rec = max(s[1] for s in antes if _igual(s[2], recorde))
            out["piso_ref"] = {"preco": recorde, "corte": rec[3], "quando": _iso(ultima_rec)}
            jan = [s for s in antes if s[1] >= agora_ - JANELA_RARIDADE * DIA]
            menor24 = min((s[2] for s in jan), default=None)
            if preco < recorde - max(10, recorde * 0.01):
                raro = (agora_ - ultima_rec) >= 548 * DIA or _metade(preco, recorde)
                out["piso_tipo"] = "raro" if raro else "novo"
            elif _igual(preco, recorde):
                out["piso_tipo"] = "igual"
            elif menor24 is not None and _igual(preco, menor24):
                out["piso_tipo"] = "24m"

    if corte <= 0:
        return out

    # ---- eixo 1: raridade pela frequencia de episodios no mesmo nivel de corte
    nivel_min = corte - TOL_NIVEL
    no_nivel = [e for e in anteriores if e[2] >= nivel_min]
    desde_jan = agora_ - JANELA_RARIDADE * DIA
    na_janela = [e for e in no_nivel if e[1] >= desde_jan]
    anos = max(0.5, (agora_ - max(t0, desde_jan)) / (365 * DIA))
    por_ano = len(na_janela) / anos
    out["eps_nivel"], out["por_ano"] = len(na_janela), round(por_ano, 2)
    out["ultima"] = _iso(no_nivel[-1][0]) if no_nivel else None
    desde = time.strftime("%m/%Y", time.gmtime(t0))  # "histórico desde 10/2021"
    # Lendario: nunca chegou a esse nivel, com 24 meses ou mais de historico e pelo menos uma promocao
    # anterior (sem promocao anterior e quase sempre buraco nos dados, ex.: ARK). Com 12-24 meses: Ultrarraro.
    antes_max = max((e[2] for e in anteriores), default=0)
    nunca = "nunca chegou a -%d%% (%shistórico desde %s)" % (
        corte, ("antes, no máximo -%d%%; " % antes_max) if antes_max else "", desde)
    if not no_nivel and dias_hist >= JANELA_RARIDADE and anteriores:
        nivel, texto = "lendario", nunca
    elif por_ano < 0.75:
        nivel = "ultrarraro"
        texto = nunca if not no_nivel else \
            "-%d%% ou mais %d vez(es) em 24 meses" % (nivel_min, len(na_janela)) if na_janela else \
            "última vez a -%d%% ou mais: %s" % (nivel_min, time.strftime("%m/%Y", time.gmtime(no_nivel[-1][0])))
    else:
        nivel = "raro" if por_ano < 1.5 else "incomum" if por_ano < 3 else "comum"
        texto = ("-%d%% ou mais %d vezes em %s (%.1f por ano)" % (
            nivel_min, len(na_janela), "24 meses" if dias_hist >= JANELA_RARIDADE else "%d meses" % out["meses"], por_ano)).replace(".", ",")
    if not anteriores and RARIDADES.index(nivel) > RARIDADES.index("incomum"):
        nivel, texto = "incomum", "nenhuma promoção anterior nas lojas marcadas (histórico desde %s)" % desde
    elif out["curto"] and RARIDADES.index(nivel) > RARIDADES.index("incomum"):
        nivel, texto = "incomum", texto + " · histórico curto (%d dias)" % dias_hist
    out["nivel"], out["texto"] = nivel, texto

    # ---- eixo 2: no piso = perto do maximo da vida (corte) ou do menor preco de 24 meses
    jan_p = [s[2] for s in segs if s[2] is not None and s[1] >= desde_jan]
    menor24_tudo = min(jan_p, default=None)
    out["no_piso"] = corte >= corte_max - TOL_NIVEL or (preco is not None and menor24_tudo is not None
                                                        and preco <= menor24_tudo * 1.01)
    # Selo (spec 04, 04/10) = so o "rare deal" (G): Recorde raro com >= 1 promocao anterior. O Lendario (F, maior
    # desconto da historia) saiu: na escada de descontos cada degrau novo virava Selo (backtest: F 67,5% x G 84,3%).
    # Sem promocao anterior nas lojas marcadas o "recorde anterior" e o preco cheio (buraco nos dados, ex.: ARK).
    minimo_selo = ((cfg_alerta or {}).get("selo_corte_minimo") or 0)
    ref = out["piso_ref"]
    if corte >= minimo_selo and out["piso_tipo"] == "raro" and anteriores and ref:
        quando = time.strftime("%m/%Y", time.gmtime(_ts(ref["quando"])))
        if _metade(preco, ref["preco"]):
            out["selo_motivo"] = "preço caiu pela metade ou mais (o menor anterior era %s, %s)" % (_brl(ref["preco"]), quando)
        else:
            meses = int((agora_ - _ts(ref["quando"])) / (30.44 * DIA))
            out["selo_motivo"] = "o menor preço anterior (%s) foi há %d meses" % (_brl(ref["preco"]), meses)
    out["selo"] = out["selo_motivo"] is not None
    out["score"] = _score_v2(corte, nivel, out["no_piso"])
    return out


TIPOS = ["selo", "novo", "igual", "24m"]  # ordem de importancia (vitrine, avisos, "Mostrar so")
NOME_TIPO = {"selo": "Selo Kurokami", "novo": "Novo recorde", "igual": "Igual ao recorde", "24m": "Menor em 2 anos"}


def tipos_de(an):
    """Tipos de preco da oferta (nao exclusivos): selo, novo (inclui "raro" sem Selo), igual, 24m."""
    t = ["selo"] if an.get("selo") else []
    pt = an.get("piso_tipo")
    if pt in ("novo", "raro"):
        t.append("novo")
    elif pt in ("igual", "24m"):
        t.append(pt)
    return t


def tipos_ligados(cfg_alerta):
    """Tipos que avisam, pelo config (alerta.tipos). Sem a chave (config antigo): so o Selo."""
    t = (cfg_alerta or {}).get("tipos") or {"selo": True}
    return [x for x in TIPOS if t.get(x)]


def avisa_por(tipos, corte, cfg_alerta):
    """Tipos ligados que fazem a oferta avisar: o Selo sempre (o selo_corte_minimo ja esta nele); os outros so com
    corte >= desconto_minimo."""
    lig = tipos_ligados(cfg_alerta)
    dmin = (cfg_alerta or {}).get("desconto_minimo", 0) or 0
    return [t for t in tipos if t in lig and (t == "selo" or (corte or 0) >= dmin)]


def tipo_oferta(tipos):
    """O tipo exclusivo (o mais importante) ou None."""
    return next((t for t in TIPOS if t in (tipos or [])), None)


def costuma_voltar(an, corte):
    """Coluna "Costuma voltar" (so informa; spec 04): (texto, ordem). ordem menor = mais raro; None = fim da lista
    ("histórico curto", "primeira promoção" e sem promocao). X = 12 / por_ano meses."""
    if not corte or not an or not an.get("nivel"):
        return None, None
    if an.get("curto"):
        return "histórico curto", None
    if not an.get("anteriores"):
        return "primeira promoção", None
    if not an.get("eps_nivel"):
        # "nunca" so se o nivel nao aparece no historico inteiro; senao so faltou nos ultimos 24 meses
        return ("não teve nos últimos 2 anos", 1) if an.get("ultima") else ("nunca teve esse desconto", 0)
    por_ano = an.get("por_ano") or 0.01
    x = 12 / por_ano
    if x < 1.5:
        txt = "todo mês"
    elif x < 10.5:
        n = round(x)
        txt = "a cada ~%d %s" % (n, "mês" if n == 1 else "meses")
    elif x < 18:
        txt = "1 vez por ano"
    else:
        txt = "1 vez em 2 anos"
    return txt, round(2 + por_ano, 3)


def dica_volta(an, corte):
    """A linha da dica (e da ficha): "Nos últimos 2 anos: N vezes com -Y% ou mais (última em mm/aaaa) · maior
    desconto que já teve: -Z%"."""
    if not corte or not an or not an.get("nivel"):
        return None
    n, ult = an.get("eps_nivel") or 0, an.get("ultima")
    return "Nos últimos 2 anos: %d %s com -%d%% ou mais%s · maior desconto que já teve: -%d%%" % (
        n, "vez" if n == 1 else "vezes", max(0, corte - TOL_NIVEL),
        " (última em %s/%s)" % (ult[5:7], ult[:4]) if ult else "", an.get("corte_max") or corte)


def motivo_tipo(an, tipo):
    """O motivo do aviso pelo tipo (A.7 da spec 04). piso_ref e o menor antes do episodio atual (de sempre,
    inclusive no 24m: o menor dos 24 meses so decide o tipo)."""
    ref = an.get("piso_ref") or {}
    quando = ("%s/%s" % (ref["quando"][5:7], ref["quando"][:4])) if ref.get("quando") else "?"
    if tipo == "selo":
        return "Selo Kurokami: " + (an.get("selo_motivo") or "")
    if tipo == "novo":
        return "menor preço já registrado (antes %s em %s)" % (_brl(ref.get("preco")), quando)
    if tipo == "igual":
        return "mesmo preço do menor já registrado (%s)" % quando
    if tipo == "24m":
        return "menor preço em 2 anos (o menor de sempre foi %s em %s)" % (_brl(ref.get("preco")), quando)
    return ""


def menor_anterior(linhas, ref):
    """O registro que fez o menor preco anterior (piso_ref): (loja, preco, quando) do ultimo registro com esse preco
    exato ate a ultima vez no nivel. None se nao achar."""
    if not ref:
        return None
    lim = ref.get("quando") or "9999"
    achados = [r for r in linhas if r["preco"] == ref["preco"] and r["quando"] <= lim]
    if not achados:
        return None
    r = max(achados, key=lambda r: r["quando"])
    return {"loja": r["loja"], "preco": r["preco"], "quando": r["quando"]}


def regua_steam(linhas, preco, corte, linhas_steam, preco_s, corte_s, agora_=None, cfg_alerta=None):
    """Regua so da Steam ("Steam (direto)" + Steam da ITAD) x lojas marcadas. Informativo, nunca avisa.
    Devolve {"steam": tipo, "radar": tipo, "loja", "preco", "quando", "texto"} quando a Steam sozinha da Novo recorde
    ou Selo e as lojas marcadas nao (ou dao um tipo menor); senao None. loja/preco/quando = o registro das lojas
    marcadas que impediu (ex.: Street Fighter 6 em 04/10/2026: Novo recorde na Steam; a Nuuvem teve R$ 68,99 em 08/2026).
    Usa analisar nas duas reguas, entao a folga de centavos da "metade" (_metade) vale nas duas."""
    if preco_s is None or not corte_s:
        return None
    an_s = analisar(linhas_steam, preco_s, corte_s, agora_=agora_, cfg_alerta=cfg_alerta)
    t_s = "selo" if an_s["selo"] else "novo" if an_s["piso_tipo"] in ("novo", "raro") else None
    if not t_s:
        return None
    an_m = analisar(linhas, preco, corte, agora_=agora_, cfg_alerta=cfg_alerta) if preco is not None else {}
    t_m = "selo" if an_m.get("selo") else "novo" if an_m.get("piso_tipo") in ("novo", "raro") else None
    if t_m == "selo" or t_m == t_s:
        return None
    imp = menor_anterior(linhas, an_m.get("piso_ref"))
    if not imp:
        return None
    texto = "Na Steam, é o menor preço já registrado. Nas suas lojas, %s já teve %s (%s/%s)." % (
        imp["loja"], _brl(imp["preco"]), imp["quando"][5:7], imp["quando"][:4])
    return {"steam": t_s, "radar": t_m, "texto": texto, **imp}


def _score_v2(corte, nivel, no_piso):
    """0-100 sem analises: corte x peso da raridade, +10 no piso."""
    return round(min(100, (corte or 0) * PESO_RARIDADE.get(nivel, 0.4) + (10 if no_piso else 0)), 1)


def favorito(jogo, cfg_alerta):
    """Esta entre os N primeiros da ordem que voce deu na lista de desejos?
    A Steam manda prioridade 0 para quem nunca ordenou: isso e "sem posicao", nao "topo"."""
    p = jogo.get("prioridade")
    return bool(p) and p <= (cfg_alerta.get("favoritos_top") or 0)


def texto_outras(a):
    """Outras lojas que tambem bateram o alerta com ate R$ 1 a mais:
    "mesmo preço na Nuuvem · na GOG por +R$ 0,40" (ate R$ 0,10 de diferenca = mesmo preco)."""
    difs = a.get("outras_dif") or [[l, 0] for l in (a.get("outras") or [])]
    iguais = [l for l, d in difs if d <= 10]
    partes = ["mesmo preço na " + " e na ".join(iguais)] if iguais else []
    partes += ["na %s por +%s" % (l, _brl(d)) for l, d in difs if d > 10]
    return " · ".join(partes)


def raridade_ok(nivel, minimo):
    return nivel in RARIDADES and RARIDADES.index(nivel) >= RARIDADES.index(minimo if minimo in RARIDADES else "raro")


def _brl(c):
    return "R$ %s" % ("%.2f" % ((c or 0) / 100)).replace(".", ",")


def tag_minima_ok(tag, cfg_alerta):
    """A etiqueta atinge o minimo que o usuario pediu para 'valer a pena'?"""
    if tag is None:
        return False
    if tag == "perto":
        return (cfg_alerta.get("perto") or {}).get("ativo", True)
    jan = cfg_alerta.get("janela_dias") or 0
    minimo = {0: "sempre", 365: "1a", 270: "9m", 180: "6m", 90: "3m"}.get(jan, "3m")
    return ORDEM_TAG[tag] >= ORDEM_TAG[minimo]


class Contexto:
    """Carrega uma vez o que a analise precisa do banco."""

    def __init__(self, banco, cfg):
        self.b, self.cfg = banco, cfg
        self.jogos = {r["appid"]: dict(r) for r in banco.q("SELECT * FROM jogo")}
        self.possuidos = {a for a, j in self.jogos.items() if j.get("possuido")}
        self.lista = {a for a, j in self.jogos.items() if j.get("na_lista")}
        self.dlcs = {}
        for r in banco.q("SELECT * FROM dlc"):
            self.dlcs.setdefault(r["pai"], []).append(dict(r))
        self.opcoes = {r["id"]: dict(r, itens=json.loads(r["itens"] or "[]")) for r in banco.q("SELECT * FROM opcao")}
        self.opcoes_do = {}
        for r in banco.q("SELECT * FROM jogo_opcao"):
            self.opcoes_do.setdefault(r["appid"], []).append(r["opcao"])

    def preco(self, appid):
        j = self.jogos.get(appid) or {}
        return j.get("preco_steam")

    def relevantes(self, appid):
        """Base + DLCs que importam (sem cosmeticos etc., conforme o config)."""
        out = []
        for d in self.dlcs.get(appid, []):
            if not dlcmod.ignorada(d["classe"], self.preco(d["appid"]), self.cfg["dlc"]):
                out.append(d["appid"])
        return out

    # ------------------------------------------------------------------ caminhos de compra
    def caminhos(self, appid):
        """Todas as formas de ter o jogo, com cobertura do conteudo relevante e custo para completar."""
        rel = [appid] + self.relevantes(appid)
        relset = set(rel)
        faltam_base = [a for a in rel if a not in self.possuidos]
        preco_av = {a: self.preco(a) for a in rel}

        def custo_avulso(itens):
            tot, sem = 0, []
            for a in itens:
                p = preco_av.get(a)
                if p is None:
                    sem.append(a)
                else:
                    tot += p
            return tot, sem

        saida = []
        base = self.jogos.get(appid) or {}
        tot, sem = custo_avulso([a for a in faltam_base if a != appid])
        saida.append({
            "id": "base", "nome": "Só o jogo base", "tipo": "base", "preco": base.get("preco_steam"),
            "cobertura": round(100 * len(relset & ({appid} | self.possuidos)) / len(relset)),
            "custo_completo": (base.get("preco_steam") or 0) + tot if base.get("preco_steam") is not None else None,
            "sem_preco": sem, "extras_lista": [],
        })
        base_cheio = base.get("cheio_steam") or 0
        for oid in self.opcoes_do.get(appid, []):
            o = self.opcoes.get(oid)
            if not o or o["final"] is None:
                continue
            itens = set(o["itens"])
            if o["tipo"] == "edicao" and o.get("papel") == "parcial":
                # ex.: HITMAN "Part One" - so um pedaco do jogo; nao serve para completar
                frac = (o["cheio"] / base_cheio) if base_cheio else 0.5
                saida.append({"id": oid, "nome": o["nome"], "tipo": "parcial", "preco": o["final"],
                              "preco_vitrine": o["final"], "desconto": o["desconto"],
                              "cobertura": round(saida[0]["cobertura"] * min(frac, 0.99)), "estimada": True,
                              "custo_completo": None, "sem_preco": [], "extras_lista": []})
                continue
            estimada = o["tipo"] == "edicao" and itens == {appid}  # conteudo da edicao ainda nao lido
            if o["tipo"] == "bundle":
                seu = self.preco_bundle_pra_voce(o)
            else:
                seu = o["final"]  # pacotes/edicoes nao descontam o que voce ja tem
            cobre = relset & (itens | self.possuidos)
            faltando = [a for a in rel if a not in itens and a not in self.possuidos]
            extra, sem = custo_avulso(faltando)
            saida.append({
                "id": oid, "nome": o["nome"], "tipo": o["tipo"], "preco": seu, "preco_vitrine": o["final"],
                "desconto": o["desconto"], "cobertura": round(100 * len(cobre) / len(relset)),
                "custo_completo": seu + extra, "sem_preco": sem, "estimada": estimada,
                "itens_que_voce_tem": len(itens & self.possuidos), "itens_total": len(itens),
                "extras_lista": [a for a in itens if a in self.lista and a != appid],
            })
        saida.sort(key=lambda c: (c["custo_completo"] is None, c["custo_completo"] or 0, -c["cobertura"]))
        return saida

    def precos_parciais(self, appid):
        return {self.opcoes[o]["final"] for o in self.opcoes_do.get(appid, [])
                if o in self.opcoes and self.opcoes[o].get("papel") == "parcial"}

    def preco_bundle_pra_voce(self, o):
        """Regra da Steam: voce paga so pelos itens que nao tem, com o desconto do bundle."""
        itens = o["itens"]
        nao_tem = [a for a in itens if a not in self.possuidos]
        if len(nao_tem) == len(itens):
            return o["final"]
        precos = {a: self.preco(a) for a in itens}
        if o.get("desconto_bundle") and all(precos[a] is not None for a in nao_tem):
            return round(sum(precos[a] for a in nao_tem) * (100 - o["desconto_bundle"]) / 100)
        total = sum(p for p in precos.values() if p)
        resto = sum(precos[a] or 0 for a in nao_tem)
        return round(o["final"] * resto / total) if total else o["final"]

    def melhor_completo(self, appid):
        return self.melhor_combinacao(appid)

    def melhor_combinacao(self, appid, max_opcoes=14):
        """Jeito mais barato de ter base + DLCs relevantes, combinando bundles/edicoes e itens avulsos.
        Ex.: HITMAN = jogo base + bundle Celebrity + bundle Deluxe Pack + o que sobrar avulso."""
        from itertools import combinations
        rel = [appid] + self.relevantes(appid)
        precisa = [a for a in rel if a not in self.possuidos]
        if not precisa:
            return {"id": "ja_tem", "nome": "você já tem tudo", "custo_completo": 0, "partes": [], "avulsos": []}
        avulso = {a: self.preco(a) for a in precisa}
        opcoes = []
        for oid in self.opcoes_do.get(appid, []) + self._opcoes_das_dlcs(appid):
            o = self.opcoes.get(oid)
            if not o or o["final"] is None or o.get("papel") == "parcial":
                continue
            cobre = frozenset(set(o["itens"]) & set(precisa))
            if not cobre:
                continue
            preco = self.preco_bundle_pra_voce(o) if o["tipo"] == "bundle" else o["final"]
            opcoes.append((preco, cobre, o["nome"], oid))
        # descarta opcoes dominadas (cobrem o mesmo ou menos por mais caro)
        opcoes.sort(key=lambda x: x[0])
        filtradas = []
        for op in opcoes:
            if not any(f[0] <= op[0] and op[1] <= f[1] for f in filtradas):
                filtradas.append(op)
        filtradas = filtradas[:max_opcoes]
        melhor = None
        for k in range(len(filtradas) + 1):
            for combo in combinations(filtradas, k):
                cobertos = set().union(*[c[1] for c in combo]) if combo else set()
                resto = [a for a in precisa if a not in cobertos]
                if any(avulso[a] is None for a in resto):
                    continue  # algum item nao e vendido avulso e ficou de fora
                total = sum(c[0] for c in combo) + sum(avulso[a] for a in resto)
                if melhor is None or total < melhor[0]:
                    melhor = (total, combo, resto)
        if melhor is None:
            return None
        total, combo, resto = melhor
        partes = [c[2] for c in combo]
        nome = " + ".join(partes + (["%d avulso(s)" % len(resto)] if resto else [])) or "avulso"
        return {"id": "combo" if combo else "base", "nome": nome, "custo_completo": total,
                "partes": [(c[2], c[0]) for c in combo], "avulsos": [(a, avulso[a]) for a in resto]}

    def _opcoes_das_dlcs(self, appid):
        """Bundles/edicoes ligados as DLCs do jogo (alem dos ligados ao proprio jogo)."""
        out = []
        dl = {d["appid"] for d in self.dlcs.get(appid, [])}
        for oid, o in self.opcoes.items():
            if oid not in self.opcoes_do.get(appid, []) and dl & set(o["itens"]):
                out.append(oid)
        return out


def avaliar(ctx, ofertas_itad, gg, lojas_marcadas):
    """Devolve a lista de alertas que dispararia agora. ofertas_itad: {appid: [oferta]}."""
    cfg = ctx.cfg
    al, ks = cfg["alerta"], cfg["keyshops"]
    tol = 1 + (al.get("tolerancia_pct") or 0) / 100
    jan = al.get("janela_dias") or 0
    alertas = []
    for appid in sorted(ctx.lista):
        j = ctx.jogos.get(appid) or {}
        if appid in ctx.possuidos:
            continue  # voce ja tem (inclusive marcado como "ja tenho" no painel)
        nome = j.get("nome") or str(appid)
        # analises da Steam nao decidem mais nada (o jogo ja esta na sua lista de desejos)
        modo = modo_do_jogo(cfg, appid)

        if modo == "completo" and ctx.dlcs.get(appid):
            m = ctx.melhor_completo(appid)
            if m:
                piso = ctx.b.menor(appid, [LOJA_COMPLETO], jan)
                ini = ctx.b.um("SELECT MIN(quando) q FROM preco WHERE appid=? AND loja=?", appid, LOJA_COMPLETO)
                from datetime import datetime, timezone
                dias = ((datetime.now(timezone.utc) - datetime.fromisoformat(ini["q"])).days
                        if ini and ini["q"] else 0)
                if dias < (cfg["alerta"].get("dias_minimos_completo") or 0):
                    continue  # "menor ja visto" so faz sentido depois de um tempo observando
                soma_cheia = sum((ctx.jogos.get(a) or {}).get("cheio_steam") or 0
                                 for a in [appid] + ctx.relevantes(appid) if a not in ctx.possuidos)
                corte = round(100 * (1 - m["custo_completo"] / soma_cheia)) if soma_cheia else 0
                if corte > 0 and piso is not None and m["custo_completo"] <= piso * tol \
                        and corte >= al.get("desconto_minimo", 0):
                    alertas.append({"appid": appid, "nome": nome, "loja": "Steam", "preco": m["custo_completo"], "corte": corte,
                                    "score": None, "tag": "completo",
                                    "motivo": "versão completa no menor valor já visto: %s" % m["nome"]})
            continue

        # ---- lojas oficiais marcadas
        parciais = ctx.precos_parciais(appid)
        pisos = None
        linhas = []
        ofs = list(ofertas_itad.get(appid, []))
        if j.get("preco_steam") is not None and not any(o["loja"] == "Steam" for o in ofs):
            ofs.append({"loja": "Steam", "preco": j["preco_steam"], "cheio": j.get("cheio_steam"),
                        "corte": j.get("desconto_steam") or 0, "drm_steam": True, "flag": None, "url": None})
        for o in ofs:
            if o["loja"] not in lojas_marcadas or not o["corte"] or o["preco"] is None:
                continue
            if cfg.get("somente_drm_steam") and not o["drm_steam"]:
                continue
            if pisos is None:
                lojas_p = list(lojas_marcadas) + (["Steam (direto)"] if "Steam" in lojas_marcadas else [])
                linhas = ctx.b.linhas_lote(lojas_p, [appid]).get(appid, [])
                pisos = ctx.b._pisos_de(linhas, (90, 180, 270, 365)) if linhas else {}
            tag, texto, acima = etiqueta(o["preco"], o.get("cheio"), pisos, al, o.get("flag"))
            an = analisar(linhas, o["preco"], o["corte"], cfg_alerta=al)
            if not an["nivel"]:
                continue
            # spec 04 (0.15): so os tipos de preco decidem aviso; raridade e favoritos nao (raridade_minima e
            # favoritos_top ficam no config, ignorados). Selo ja tem o selo_corte_minimo dentro; os outros, desconto_minimo.
            tipos = tipos_de(an)
            por = avisa_por(tipos, o["corte"], al)
            if not por:
                continue
            t_of = tipo_oferta(tipos)
            alertas.append({"appid": appid, "nome": nome, "loja": o["loja"], "preco": o["preco"], "corte": o["corte"],
                            "score": an["score"], "url": o.get("url"), "tag": tag, "acima": acima,
                            "raridade": an["nivel"], "raridade_texto": an["texto"], "selo": an["selo"],
                            "selo_motivo": an["selo_motivo"], "piso_tipo": an["piso_tipo"], "menor_sempre": pisos.get(0),
                            "tipos": tipos, "tipo_oferta": t_of, "avisa_por": por, "motivo": motivo_tipo(an, t_of)})

        # ---- keyshops, so quando muito barato
        g = gg.get(appid)
        if ks.get("ativo") and g and g.get("keyshop") is not None and not parciais and not g.get("parcial"):
            kp = g["keyshop"]
            pisos_of = [x for x in (ctx.b.menor(appid, list(lojas_marcadas)), g.get("hist_oficial")) if x]
            menor_of = min(pisos_of) if pisos_of else None
            barato = kp <= (ks.get("preco_maximo") or 0) * 100 or \
                (menor_of and kp <= menor_of * (ks.get("pct_do_menor_oficial") or 0) / 100)
            no_piso = g.get("hist_keyshop") is not None and kp <= g["hist_keyshop"] * tol
            if barato and no_piso:
                alertas.append({"appid": appid, "nome": nome, "loja": "Keyshop (GG.deals)", "preco": kp, "corte": None, "tag": "keyshop",
                                "score": None, "url": g.get("url"), "motivo": "keyshop no menor histórico e bem abaixo do oficial"})
    # um alerta por jogo: a oferta mais barata, citando as outras lojas no mesmo preco (ate R$ 1 de diferenca)
    por_jogo = {}
    for a in alertas:
        por_jogo.setdefault(a["appid"], []).append(a)
    final = []
    for lst in por_jogo.values():
        lst.sort(key=lambda a: (a["preco"], ordem_tipo(a.get("tipo_oferta")), a["loja"] != "Steam"))
        top = dict(lst[0])
        perto = [x for x in lst[1:] if x["preco"] - top["preco"] <= 100 and x["loja"] != top["loja"]]
        top["outras"] = [x["loja"] for x in perto]
        top["outras_dif"] = [[x["loja"], x["preco"] - top["preco"]] for x in perto]  # centavos a mais
        final.append(top)
    final.sort(key=chave_aviso)
    return final


def ordem_tipo(t):
    return TIPOS.index(t) if t in TIPOS else len(TIPOS)


def chave_aviso(a):
    """Ordem dos avisos (e do max_por_rodada): selo, novo, igual, 24m (keyshop e completo depois); maior corte primeiro."""
    return (ordem_tipo(a.get("tipo_oferta")), -(a.get("corte") or 0), a.get("nome") or "")
