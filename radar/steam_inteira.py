"""Promocoes da Steam inteira (spec 07): IStoreQueryService/Query, sem chave, 1.000 itens por chamada.

- So vem quem esta com desconto; o retrato fica em steam_promo e cada coleta substitui tudo (sem historico:
  decisao do dono, o espaco fica sempre do tamanho de uma coleta).
- sort 2 e obrigatorio: sem ele a paginacao repete e pula itens (spec 04, 1.6).
- Coleta incompleta (erro no meio) nao troca o retrato: quem nao foi visto continua la ate a proxima completa."""
import json
import time
import urllib.parse

from . import progresso
from .banco import agora
from .rede import RITMO, http_json

QUERY = "https://api.steampowered.com/IStoreQueryService/Query/v1/"
POR_CHAMADA = 1000
MAX_CHAMADAS = 300   # ~300 mil itens: folga sobre os ~108 mil de uma grande promocao
TIPOS = {0: "jogo", 4: "dlc"}
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


def coletar(banco, cfg, log=print):
    """Baixa as promocoes e substitui o retrato. Devolve quantos itens."""
    t0 = time.time()
    progresso.etapa("Steam inteira", None)
    novos, chamadas = baixar(str(cfg.get("pais") or "BR").upper())
    quando = agora()
    cols = ("appid", "tipo", "nome", "pacote", "preco", "cheio", "corte", "fim", "rpos", "rcount", "rotulo", "lancamento", "capa")
    banco.con.execute("DELETE FROM steam_promo")
    banco.con.executemany("INSERT INTO steam_promo(%s, visto) VALUES(%s)" % (", ".join(cols), ", ".join("?" * (len(cols) + 1))),
                          [tuple(n[c] for c in cols) + (quando,) for n in novos.values()])
    banco.meta("ult_steam_inteira", quando)
    banco.meta("steam_inteira_resumo", {"itens": len(novos), "chamadas": chamadas, "segundos": round(time.time() - t0)})
    banco.commit()
    log("Steam inteira: %d itens em promocao (%d chamadas, %.0fs)" % (len(novos), chamadas, time.time() - t0))
    return len(novos)
