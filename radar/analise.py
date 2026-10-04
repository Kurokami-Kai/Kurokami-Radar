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
    no_piso, selo, piso_tipo, piso_ref, score. nivel/piso_tipo sao None se nao ha promocao."""
    import time
    agora_ = agora_ or time.time()
    segs = linha_do_tempo(linhas, agora_)
    corte = corte or 0
    out = {"nivel": None, "texto": None, "por_ano": None, "eps_nivel": 0, "ultima": None, "corte_max": corte,
           "meses": 0, "curto": True, "inicio": None, "no_piso": False, "selo": False,
           "piso_tipo": None, "piso_ref": None, "score": 0}
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
                raro = (agora_ - ultima_rec) >= 548 * DIA or preco <= recorde * 0.5
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
    desde = time.gmtime(t0).tm_year
    # Lendario: nunca chegou a esse nivel, com 24 meses ou mais de historico e pelo menos uma promocao
    # anterior (sem promocao anterior e quase sempre buraco nos dados, ex.: ARK). Com 12-24 meses: Ultrarraro.
    if not no_nivel and dias_hist >= JANELA_RARIDADE and anteriores:
        nivel, texto = "lendario", "nunca chegou a -%d%% (histórico desde %d)" % (nivel_min, desde)
    elif por_ano < 0.75:
        nivel = "ultrarraro"
        texto = ("nunca chegou a -%d%% (histórico desde %d)" % (nivel_min, desde)) if not no_nivel else \
            "-%d%% ou mais %d vez(es) em 24 meses" % (nivel_min, len(na_janela)) if na_janela else \
            "última vez a -%d%% ou mais: %s" % (nivel_min, time.strftime("%m/%Y", time.gmtime(no_nivel[-1][0])))
    else:
        nivel = "raro" if por_ano < 1.5 else "incomum" if por_ano < 3 else "comum"
        texto = ("-%d%% ou mais %d vezes em %s (%.1f por ano)" % (
            nivel_min, len(na_janela), "24 meses" if dias_hist >= JANELA_RARIDADE else "%d meses" % out["meses"], por_ano)).replace(".", ",")
    if not anteriores and RARIDADES.index(nivel) > RARIDADES.index("incomum"):
        nivel, texto = "incomum", "nenhuma promoção anterior nas lojas marcadas (histórico desde %d)" % desde
    elif out["curto"] and RARIDADES.index(nivel) > RARIDADES.index("incomum"):
        nivel, texto = "incomum", texto + " · histórico curto (%d dias)" % dias_hist
    out["nivel"], out["texto"] = nivel, texto

    # ---- eixo 2: no piso = perto do maximo da vida (corte) ou do menor preco de 24 meses
    jan_p = [s[2] for s in segs if s[2] is not None and s[1] >= desde_jan]
    menor24_tudo = min(jan_p, default=None)
    out["no_piso"] = corte >= corte_max - TOL_NIVEL or (preco is not None and menor24_tudo is not None
                                                        and preco <= menor24_tudo * 1.01)
    minimo_selo = ((cfg_alerta or {}).get("selo_corte_minimo") or 0)
    out["selo"] = bool(out["no_piso"] and RARIDADES.index(nivel) >= RARIDADES.index("raro")
                       and dias_hist >= 365 and corte >= minimo_selo)
    out["score"] = _score_v2(corte, nivel, out["no_piso"])
    return out


def _score_v2(corte, nivel, no_piso):
    """0-100 sem analises: corte x peso da raridade, +10 no piso."""
    return round(min(100, (corte or 0) * PESO_RARIDADE.get(nivel, 0.4) + (10 if no_piso else 0)), 1)


def favorito(jogo, cfg_alerta):
    """Esta entre os N primeiros da ordem que voce deu na lista de desejos?
    A Steam manda prioridade 0 para quem nunca ordenou: isso e "sem posicao", nao "topo"."""
    p = jogo.get("prioridade")
    return bool(p) and p <= (cfg_alerta.get("favoritos_top") or 0)


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
        fav = favorito(j, al)
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
            minimo = al.get("raridade_minima") or "raro"
            if fav and RARIDADES.index(minimo if minimo in RARIDADES else "raro") > 1:
                minimo = "incomum"  # favoritos (topo da sua lista) avisam a partir de Incomum
            if not an["selo"] and not (raridade_ok(an["nivel"], minimo)
                                       and (fav or o["corte"] >= al.get("desconto_minimo", 0))):
                continue
            motivo = ("Selo Kurokami: " if an["selo"] else "") + "%s: %s" % (NOME_RARIDADE[an["nivel"]], an["texto"])
            alertas.append({"appid": appid, "nome": nome, "loja": o["loja"], "preco": o["preco"], "corte": o["corte"],
                            "score": an["score"], "url": o.get("url"), "tag": tag, "acima": acima, "favorito": fav,
                            "raridade": an["nivel"], "raridade_texto": an["texto"], "selo": an["selo"],
                            "piso_tipo": an["piso_tipo"], "menor_sempre": pisos.get(0),
                            "motivo": motivo + (" · favorito da sua lista" if fav else "")})

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
        lst.sort(key=lambda a: (a["preco"], -RARIDADES.index(a["raridade"]) if a.get("raridade") in RARIDADES else 0,
                                a["loja"] != "Steam"))
        top = dict(lst[0])
        top["outras"] = [x["loja"] for x in lst[1:] if x["preco"] - top["preco"] <= 100 and x["loja"] != top["loja"]]
        final.append(top)
    final.sort(key=lambda a: (not a.get("selo"), -(RARIDADES.index(a["raridade"]) if a.get("raridade") in RARIDADES else -1),
                              -(a["score"] or 0)))
    return final
