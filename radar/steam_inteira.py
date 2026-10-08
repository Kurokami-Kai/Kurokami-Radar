"""Promocoes da Steam inteira (spec 07): IStoreQueryService/Query, sem chave, 1.000 itens por chamada.

- So vem quem esta com desconto; o retrato fica em steam_promo e cada coleta substitui tudo (sem historico:
  decisao do dono, o espaco fica sempre do tamanho de uma coleta).
- sort 2 e obrigatorio: sem ele a paginacao repete e pula itens (spec 04, 1.6).
- Coleta incompleta (erro no meio) nao troca o retrato: quem nao foi visto continua la ate a proxima completa.
- Recordes (08/10, pedido do dono): a ITAD da em lote a marca da oferta da Steam (N novo recorde, H igual) e os
  menores de sempre/1 ano; o historico completo (lojas marcadas) so de quem esta perto do recorde, aos poucos
  (historicos), e com ele a avaliacao e a mesma da lista (analise.analisar): Selo, Menor em 2 anos, Costuma voltar."""
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import analise, itad, progresso
from .banco import agora, utc
from .rede import RITMO, explicar, http_json

QUERY = "https://api.steampowered.com/IStoreQueryService/Query/v1/"
POR_CHAMADA = 1000
MAX_CHAMADAS = 300   # ~300 mil itens: folga sobre os ~108 mil de uma grande promocao
TIPOS = {0: "jogo", 4: "dlc"}
LOTES_ITAD = 20      # por rodada, no mapeamento e nas marcas (4 mil itens): a ITAD aceita ~100 chamadas em 5 min e a lista vem logo depois
CDN = "https://shared.fastly.steamstatic.com/store_item_assets/"


def _pedido(start, pais):
    return {"query": {"start": start, "count": POR_CHAMADA, "sort": 2,
                      "filters": {"type_filters": {"include_apps": True, "include_dlc": True},
                                  "price_filters": {"min_discount_percent": 1}}},
            "context": {"language": "brazilian", "country_code": pais},
            "data_request": {"include_release": True, "include_reviews": True, "include_assets": True}}


def _capa(it):
    a = it.get("assets") or {}
    fmt, arq = a.get("asset_url_format"), a.get("header")
    return CDN + fmt.replace("${FILENAME}", arq) if fmt and arq else None


def normalizar(it):
    """Item da Query -> linha de steam_promo, ou None se nao for compravel/sem desconto."""
    op = it.get("best_purchase_option") or {}
    appid = it.get("appid") or it.get("id")
    if not appid or not op.get("final_price_in_cents") or not op.get("discount_pct"):
        return None
    rv = (it.get("reviews") or {}).get("summary_filtered") or {}
    fins = [d.get("discount_end_date") for d in op.get("active_discounts") or [] if d.get("discount_end_date")]
    return {"appid": int(appid), "tipo": TIPOS.get(it.get("type"), "outro"), "nome": it.get("name") or str(appid),
            "pacote": op.get("packageid") or None, "preco": int(op["final_price_in_cents"]),
            "cheio": int(op.get("original_price_in_cents") or op["final_price_in_cents"]), "corte": int(op["discount_pct"]),
            "fim": min(fins) if fins else None, "rpos": rv.get("percent_positive"),
            "rcount": (rv.get("review_count") or 0) if rv.get("percent_positive") is not None else 0,
            "rotulo": rv.get("review_score_label") or "", "lancamento": (it.get("release") or {}).get("steam_release_date"),
            "capa": _capa(it)}


def baixar(pais, max_chamadas=MAX_CHAMADAS):
    """{appid: linha} de todas as promocoes da Steam. Levanta excecao se nao conseguir ler tudo."""
    itens, start, total, chamadas = {}, 0, None, 0
    while chamadas < max_chamadas:
        url = QUERY + "?" + urllib.parse.urlencode({"input_json": json.dumps(_pedido(start, pais), separators=(",", ":"))})
        r = (http_json(url, ritmo=RITMO["steam"], timeout=90) or {}).get("response") or {}
        chamadas += 1
        lote = r.get("store_items") or []
        total = (r.get("metadata") or {}).get("total_matching_records", total)
        for it in lote:
            n = normalizar(it)
            if n:
                itens[n["appid"]] = n
        start += len(lote)
        if total:
            progresso.passo(min(start, total), total)
        if not lote or (total is not None and start >= total):
            if total is None or start < total or (total and not itens):   # resposta vazia/cortada: nao troca o retrato
                raise RuntimeError("Steam inteira: a Steam parou em %d de %s itens" % (start, total))
            return itens, chamadas
    raise RuntimeError("Steam inteira: passou de %d chamadas sem terminar" % max_chamadas)


def _mapear(banco, chave, appids, log):
    """{appid: gid} pela ITAD, guardado em promo_estado (gid '' = a ITAD nao conhece; tenta de novo em 30 dias).
    appids em ordem de prioridade; no maximo LOTES_ITAD lotes por rodada (o resto fica para a proxima). Os jogos da
    lista ja mapeados (meta itad_ids) nao gastam chamada. Erro no meio: guarda o que ja veio."""
    conhecidos = {r["appid"]: (r["gid"], r["mapeado"] or "") for r in banco.q("SELECT appid, gid, mapeado FROM promo_estado")}
    limite = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    faltam = [a for a in appids if a not in conhecidos or (not conhecidos[a][0] and conhecidos[a][1] < limite)]
    if faltam:
        da_lista = banco.meta("itad_ids") or {}
        cache = {str(a): da_lista[str(a)] for a in faltam if da_lista.get(str(a))}
        pedir = [a for a in faltam if str(a) not in cache][:LOTES_ITAD * 200]
        try:
            itad.mapear(chave, pedir, cache)
        except itad.ChaveRecusada:
            raise
        except Exception as e:
            log("   mapeamento na ITAD parou (%s); continuo na proxima rodada" % explicar(e))
        quando = agora()
        feitos = [a for a in faltam if str(a) in cache]
        banco.con.executemany(
            "INSERT INTO promo_estado(appid, gid, mapeado) VALUES(?,?,?) "
            "ON CONFLICT(appid) DO UPDATE SET gid=excluded.gid, mapeado=excluded.mapeado",
            [(a, cache[str(a)] or "", quando) for a in feitos])
        banco.commit()
        for a in feitos:
            conhecidos[a] = (cache[str(a)] or "", quando)
    return {a: conhecidos[a][0] for a in appids if conhecidos.get(a, ("",))[0]}


def _marcas(banco, chave, pais, novos, log):
    """Preenche gid, flag, hl, hl1 de cada item. A marca e os menores ficam em promo_estado e so sao pedidos de novo
    quando o preco muda ou passou 1 dia (numa grande promocao sao ~540 lotes: de hora em hora estouraria a cota)."""
    ordem = sorted(novos, key=lambda a: (novos[a]["tipo"] != "jogo", -(novos[a]["rcount"] or 0), a))   # populares primeiro
    gids = _mapear(banco, chave, ordem, log)
    guardado = {r["appid"]: r for r in banco.q("SELECT appid, flag, hl, hl1, menores_preco, menores_quando FROM promo_estado")}
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    pedir = {}
    for a in ordem:
        g = gids.get(a)
        if not g:
            continue
        e = guardado.get(a)
        if e and e["menores_preco"] == novos[a]["preco"] and (e["menores_quando"] or "") >= ontem:
            novos[a].update(gid=g, flag=e["flag"], hl=e["hl"], hl1=e["hl1"])
        else:
            pedir.setdefault(g, []).append(a)
    if pedir:
        info = itad.menores(chave, pais, list(pedir)[:LOTES_ITAD * 200], log)   # pedir segue a prioridade
        quando = agora()
        linhas = []
        for g, apps in pedir.items():
            i = info.get(g)
            for a in apps:
                novos[a]["gid"] = g
                if i is None:   # lote falhou: fica o que o coletar ja trouxe do guardado (mesmo preco) e tenta na proxima
                    continue
                novos[a].update(i)
                linhas.append((i["flag"], i["hl"], i["hl1"], novos[a]["preco"], quando, a))
        banco.con.executemany("UPDATE promo_estado SET flag=?, hl=?, hl1=?, menores_preco=?, menores_quando=? WHERE appid=?", linhas)
        banco.commit()


def avaliar(banco, cfg, itens):
    """Preenche it["aval"] (JSON) de cada item {appid: {preco, corte, flag}}: com historico, a mesma avaliacao da
    lista (lojas marcadas); sem ele, so a marca da ITAD (N novo recorde, H igual ao recorde) ate o historico chegar.
    Le o historico agrupado por jogo (sem carregar tudo na memoria)."""
    lojas = set((banco.meta("promo_lojas") or {}).get("nomes") or [])
    com_hist = {r["appid"] for r in banco.q("SELECT appid FROM promo_estado WHERE baixado IS NOT NULL")} & set(itens)
    al = cfg["alerta"]

    def com(a, linhas):
        feitos.add(a)
        it = itens[a]
        try:
            an = analise.analisar(linhas, it["preco"], it["corte"], cfg_alerta=al)
        except Exception:   # um jogo com dado estranho fica com a marca da ITAD; nao derruba o retrato
            return
        volta, ordem = analise.costuma_voltar(an, it["corte"])
        it["aval"] = json.dumps({"tipos": analise.tipos_de(an), "selo_motivo": an["selo_motivo"], "piso_ref": an["piso_ref"],
                                 "volta_texto": volta, "volta_ordem": ordem, "volta_dica": analise.dica_volta(an, it["corte"]),
                                 "inicio": an["inicio"]}, separators=(",", ":"))
    for it in itens.values():
        t = {"N": ["novo"], "H": ["igual"]}.get(it.get("flag"))
        it["aval"] = json.dumps({"tipos": t, "provisorio": True}) if t else None
    if not com_hist or not lojas:
        return
    feitos = set()
    atual, linhas = None, []
    # linha_do_tempo ordena cada loja por conta propria: ORDER BY appid usa a chave primaria (sem ordenar a tabela)
    for r in banco.con.execute("SELECT appid, loja, preco, corte, quando FROM promo_hist ORDER BY appid"):
        if r[0] != atual:
            if atual in com_hist:
                com(atual, linhas)
            atual, linhas = r[0], []
        if r[1] in lojas:
            linhas.append({"loja": r[1], "preco": r[2], "corte": r[3], "quando": r[4]})
    if atual in com_hist:
        com(atual, linhas)
    for a in com_hist - feitos:   # historico baixado, mas sem nada nas lojas marcadas
        com(a, [])


def coletar(banco, cfg, log=print, chave_itad=None):
    """Baixa as promocoes, junta a marca e os menores da ITAD, avalia com o historico que ja tem e substitui o
    retrato (tudo antes de gravar: o painel nunca ve o retrato sem recordes). Devolve quantos itens."""
    t0 = time.time()
    progresso.etapa("Steam inteira", None)
    pais = str(cfg.get("pais") or "BR").upper()
    novos, chamadas = baixar(pais)
    t_steam = time.time() - t0
    guardado = {r["appid"]: r for r in banco.q("SELECT appid, flag, hl, hl1, menores_preco FROM promo_estado")}
    for a, n in novos.items():
        e = guardado.get(a)
        mesmo = e is not None and e["menores_preco"] == n["preco"]
        n.update(flag=e["flag"] if mesmo else None, hl=e["hl"] if mesmo else None, hl1=e["hl1"] if mesmo else None)
    if chave_itad:
        try:
            _marcas(banco, chave_itad, pais, novos, log)
        except Exception as e:   # sem a ITAD o retrato sai com as marcas guardadas; tenta de novo na proxima
            log("   recordes da Steam inteira pela ITAD falharam (%s)" % explicar(e))
    avaliar(banco, cfg, novos)
    quando = agora()
    cols = ("appid", "tipo", "nome", "pacote", "preco", "cheio", "corte", "fim", "rpos", "rcount", "rotulo", "lancamento",
            "capa", "flag", "hl1", "aval")
    banco.con.execute("DELETE FROM steam_promo")
    banco.con.executemany("INSERT INTO steam_promo(%s, visto) VALUES(%s)" % (", ".join(cols), ", ".join("?" * (len(cols) + 1))),
                          [tuple(n[c] for c in cols) + (quando,) for n in novos.values()])
    banco.con.execute("UPDATE promo_estado SET visto=? WHERE appid IN (SELECT appid FROM steam_promo)", (quando,))
    banco.meta("ult_steam_inteira", quando)
    banco.meta("promo_avaliado", quando)
    banco.meta("steam_inteira_resumo", {"itens": len(novos), "chamadas": chamadas, "segundos": round(time.time() - t0)})
    banco.commit()
    log("Steam inteira: %d itens em promocao (%d chamadas, %.0fs; com recordes da ITAD: %.0fs)" % (
        len(novos), chamadas, t_steam, time.time() - t0))
    return len(novos)


def _perto(r):
    """Pode ser recorde (vale baixar o historico): marca da ITAD ou preco no menor de 1 ano."""
    return r["flag"] in ("N", "H", "S") or (r["hl1"] is not None and (r["preco"] <= r["hl1"] or analise._igual(r["preco"], r["hl1"])))


def historicos(banco, cfg, chave, log=print, por_rodada=60):
    """Baixa o historico (lojas marcadas, pela ITAD) de quem esta perto do recorde, aos poucos (`por_rodada` jogos;
    primeiro os novos recordes, jogos antes de DLCs, os mais avaliados antes) e reavalia o retrato. No limite de
    ritmo da ITAD para na hora (sem esperar) e continua na proxima rodada.
    Ja baixado: so busca o que veio depois, quando o preco mudou (ou a cada 7 dias). Devolve quantos baixou."""
    pais = str(cfg.get("pais") or "BR").upper()
    # quem saiu da Steam inteira ha 60 dias (ou foi mapeado numa coleta que nao terminou) deixa de ocupar espaco
    velho = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    banco.con.execute("DELETE FROM promo_hist WHERE appid IN (SELECT appid FROM promo_estado WHERE COALESCE(visto, mapeado) < ?)", (velho,))
    banco.con.execute("DELETE FROM promo_estado WHERE COALESCE(visto, mapeado) < ?", (velho,))
    banco.commit()
    agora_ = datetime.now(timezone.utc)
    h1, d7 = (agora_ - timedelta(hours=1)).isoformat(), (agora_ - timedelta(days=7)).isoformat()
    fila = []
    for r in banco.q("SELECT p.appid, p.tipo, p.preco, p.rcount, p.flag, p.hl1, e.gid, e.baixado, e.preco_baixado "
                     "FROM steam_promo p JOIN promo_estado e ON e.appid=p.appid WHERE e.gid != ''"):
        if not _perto(r):
            continue
        if not r["baixado"]:
            pri = 0
        elif r["preco_baixado"] != r["preco"] and r["baixado"] < h1:
            pri = 1
        elif r["baixado"] < d7:
            pri = 2
        else:
            continue
        fila.append((pri, r["flag"] != "N", r["tipo"] != "jogo", -(r["rcount"] or 0), r["appid"], r))
    fila.sort(key=lambda x: x[:5])
    if not fila:
        return 0
    achadas, _faltando, _todas = itad.resolver_lojas(chave, pais, cfg["lojas"])
    ids, nomes = sorted(achadas), sorted(achadas.values())
    if ids and (banco.meta("promo_lojas") or {}).get("ids") != ids:   # mudaram as lojas marcadas: historico de novo
        banco.con.execute("DELETE FROM promo_hist")
        banco.con.execute("UPDATE promo_estado SET baixado=NULL, preco_baixado=NULL")
        banco.meta("promo_lojas", {"ids": ids, "nomes": nomes})
        banco.commit()
        return historicos(banco, cfg, chave, log, por_rodada)   # a fila muda (todos voltam a "nunca baixado")
    if not ids:
        return 0
    feitos, t0 = 0, time.time()
    lote = fila[:por_rodada]
    if lote:
        log("Steam inteira: historico de %d de %d itens perto do recorde..." % (len(lote), len(fila)))
        progresso.etapa("Histórico da Steam inteira", len(lote))
    for i, f in enumerate(lote, 1):
        r = f[-1]
        progresso.passo(i, len(lote))
        desde = (datetime.fromisoformat(r["baixado"]) - timedelta(days=2)).isoformat() if r["baixado"] else None
        try:
            regs = itad.historico(chave, pais, r["gid"], ids, cfg["historico"]["importar_dias"], desde=desde, tentativas=1)
        except itad.ChaveRecusada:
            raise
        except Exception as e:
            log("   a ITAD limitou o ritmo (%s); continuo na proxima rodada" % explicar(e))
            break
        banco.con.executemany("INSERT OR IGNORE INTO promo_hist VALUES(?,?,?,?,?,?)",
                              [(r["appid"], g[0], g[1], g[2], g[3], utc(g[4])) for g in regs if g[1] is not None])
        banco.con.execute("UPDATE promo_estado SET baixado=?, preco_baixado=? WHERE appid=?", (agora(), r["preco"], r["appid"]))
        feitos += 1
        if feitos % 10 == 0:
            banco.commit()
    itens = {r["appid"]: dict(r) for r in banco.q("SELECT appid, preco, corte, flag FROM steam_promo")}
    avaliar(banco, cfg, itens)
    banco.con.executemany("UPDATE steam_promo SET aval=? WHERE appid=?", [(it["aval"], a) for a, it in itens.items()])
    banco.meta("promo_avaliado", agora())
    banco.commit()
    log("   %d historicos baixados em %.0fs (faltam %d)" % (feitos, time.time() - t0, len(fila) - feitos))
    return feitos
