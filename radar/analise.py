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


def raridade(linhas, preco, flag=None):
    """Quao raro e este preco no historico do jogo (lojas que alertam).
    Olha o MENOR preco entre as lojas ao longo do tempo e mede, ANTES do episodio atual:
    quanto tempo o jogo ficou neste preco ou menos e quantas vezes isso aconteceu.
      Lendario  : nunca esteve tao barato (novo recorde)
      Ultrarraro: menos de 2% do tempo, ou so 1 vez antes em 1 ano+ de historico
      Raro      : menos de 8% do tempo
      Incomum   : menos de 20% do tempo
      Comum     : acontece com frequencia
    Devolve {"nivel", "texto", "fracao", "vezes", "desde", "curto"} ou None."""
    import time
    from datetime import datetime
    if preco is None:
        return None
    VALIDADE_PROMO = 45 * 86400  # uma promocao sem registro de fim "acaba" sozinha depois disso
    agora_ = time.time()
    por_loja = {}
    for r in linhas:
        if not r["preco"] and preco:
            continue  # brindes (R$ 0) nao contam como preco
        try:
            t = datetime.fromisoformat(str(r["quando"]).replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        corte = r["corte"] if "corte" in r.keys() else 0
        por_loja.setdefault(r["loja"], []).append((t, r["preco"], corte or 0))
    if not por_loja:
        return None
    # cada registro vale ate o proximo da mesma loja; promocao sem fim registrado vence em 45 dias
    # (sem isso, uma loja que parou de vender o jogo em promocao ficaria "em promocao" para sempre)
    eventos = []
    for loja, regs in por_loja.items():
        regs.sort()
        for k, (t, p, c) in enumerate(regs):
            fim = regs[k + 1][0] if k + 1 < len(regs) else agora_ + 1
            if c > 0:
                fim = min(fim, t + VALIDADE_PROMO)
            if fim > t:
                eventos.append((t, 1, loja, p, fim))
                eventos.append((fim, 0, loja, p, fim))
    eventos.sort(key=lambda e: (e[0], e[1]))
    limiar = preco + max(10, preco * 0.01)  # centavos de diferenca contam como igual
    ativos, linha = {}, []
    for t, tipo, loja, p, fim in eventos:
        if tipo == 1:
            ativos[loja] = (p, fim)
        elif loja in ativos and ativos[loja][1] == fim:
            del ativos[loja]
        m = min((v[0] for v in ativos.values()), default=None)
        if linha and linha[-1][0] == t:
            linha[-1] = (t, m)
        else:
            linha.append((t, m))
    linha = [(t, m) for t, m in linha if t <= agora_]
    if not linha or all(m is None for _, m in linha):
        return None
    while linha and linha[0][1] is None:
        linha.pop(0)
    t0 = linha[0][0]
    # inicio do episodio atual (a ultima vez que o menor preco caiu para <= limiar)
    inicio = agora_
    for i in range(len(linha) - 1, -1, -1):
        if linha[i][1] is not None and linha[i][1] <= limiar:
            inicio = linha[i][0]
        else:
            break
    tempo_le, vezes, dentro, menor_antes = 0.0, 0, False, None
    for i, (t, m) in enumerate(linha):
        if t >= inicio:
            break
        fim = min(linha[i + 1][0] if i + 1 < len(linha) else agora_, inicio)
        if m is None:
            dentro = False
            continue
        menor_antes = m if menor_antes is None else min(menor_antes, m)
        if m <= limiar:
            tempo_le += max(0, fim - t)
            if not dentro:
                vezes += 1
            dentro = True
        else:
            dentro = False
    span = max(1.0, inicio - t0)
    dias = span / 86400
    fracao = tempo_le / span
    desde = datetime.fromtimestamp(t0).year
    curto = dias < 180
    if flag == "N" or menor_antes is None or vezes == 0 or preco < menor_antes - max(10, menor_antes * 0.01):
        nivel = "lendario"
        texto = "nunca esteve tão barato (histórico desde %d)" % desde
    elif fracao < 0.02 or (vezes <= 1 and dias >= 365):
        nivel = "ultrarraro"
        texto = ("só %d vez antes nesse preço, desde %d" % (vezes, desde)) if vezes <= 1 else \
                "esteve assim só %.1f%% do tempo (%d vezes desde %d)" % (100 * fracao, vezes, desde)
    elif fracao < 0.08:
        nivel, texto = "raro", "esteve assim %d%% do tempo (%d vezes desde %d)" % (round(100 * fracao) or 1, vezes, desde)
    elif fracao < 0.20:
        nivel, texto = "incomum", "esteve assim %d%% do tempo (%d vezes desde %d)" % (round(100 * fracao), vezes, desde)
    else:
        nivel, texto = "comum", "esteve assim %d%% do tempo: promoção frequente" % round(100 * fracao)
    if curto:  # pouco historico: nao da para afirmar raridade alta
        if dias < 60:
            nivel, texto = "comum", "histórico curto (%d dias): raridade ainda incerta" % dias
        elif RARIDADES.index(nivel) > RARIDADES.index("raro"):
            nivel, texto = "raro", texto + " · histórico curto (%d dias)" % dias
    return {"nivel": nivel, "texto": texto, "fracao": round(fracao, 4), "vezes": vezes, "desde": desde, "curto": curto}


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


def qualidade(rpos, rcount):
    """% positivas puxado para 70 quando ha poucas analises (40 analises 'virtuais')."""
    n = rcount or 0
    if not n:
        return None
    return ((rpos or 0) * n + 70 * 40) / (n + 40)


def score(corte, rpos, rcount):
    q = qualidade(rpos, rcount)
    return round((corte or 0) * (q if q is not None else 60) / 100, 1)


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
        rpos, rcount = j.get("rpos") or 0, j.get("rcount") or 0
        fav = j.get("prioridade") is not None and j["prioridade"] < (al.get("favoritos_top") or 0)
        if not fav and al.get("ignorar_sem_avaliacoes") and not rcount:
            continue
        if not fav and al.get("avaliacao_minima") and rcount and rpos < al["avaliacao_minima"]:
            continue
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
                sc = score(corte, rpos, rcount)
                if corte > 0 and piso is not None and m["custo_completo"] <= piso * tol and sc >= al.get("score_minimo", 0) \
                        and corte >= al.get("desconto_minimo", 0):
                    alertas.append({"appid": appid, "nome": nome, "loja": "Steam", "preco": m["custo_completo"], "corte": corte,
                                    "score": sc, "tag": "completo",
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
            sc = score(o["corte"], rpos, rcount)
            if not fav and (sc < al.get("score_minimo", 0) or o["corte"] < al.get("desconto_minimo", 0)):
                continue  # favoritos (topo da sua lista) so precisam bater o piso
            if pisos is None:
                lojas_p = list(lojas_marcadas) + (["Steam (direto)"] if "Steam" in lojas_marcadas else [])
                linhas = ctx.b.linhas_lote(lojas_p, [appid]).get(appid, [])
                pisos = ctx.b._pisos_de(linhas, (90, 180, 270, 365)) if linhas else {}
            tag, texto, acima = etiqueta(o["preco"], o.get("cheio"), pisos, al, o.get("flag"))
            rar = raridade(linhas, o["preco"], o.get("flag")) if linhas else None
            minimo = al.get("raridade_minima") or "raro"
            if rar and raridade_ok(rar["nivel"], "incomum" if fav and RARIDADES.index(minimo) > 1 else minimo):
                alertas.append({"appid": appid, "nome": nome, "loja": o["loja"], "preco": o["preco"], "corte": o["corte"],
                                "score": sc, "url": o.get("url"), "tag": tag, "acima": acima, "favorito": fav,
                                "raridade": rar["nivel"], "raridade_texto": rar["texto"],
                                "menor_sempre": pisos.get(0),
                                "motivo": "%s: %s" % (NOME_RARIDADE[rar["nivel"]], rar["texto"]) + (" · favorito da sua lista" if fav else "")})

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
    final.sort(key=lambda a: (-(RARIDADES.index(a["raridade"]) if a.get("raridade") in RARIDADES else -1), -(a["score"] or 0)))
    return final
