"""IsThereAnyDeal: lojas, mapeamento de ids, precos por loja (com DRM) e historico."""
import re
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import cambio
from .rede import RITMO, de_reais, explicar, http_json, lotes

API = "https://api.isthereanydeal.com/"
SHOP_STEAM = 61


class ChaveRecusada(Exception):
    pass


def _get(caminho, chave, tentativas=4, **params):
    params["key"] = chave
    try:
        return http_json(API + caminho + "?" + urllib.parse.urlencode(params, doseq=True), ritmo=RITMO["itad"],
                         tentativas=tentativas)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ChaveRecusada("a IsThereAnyDeal recusou a chave (%s)" % explicar(e))
        raise


def _post(caminho, chave, corpo, **params):
    params["key"] = chave
    try:
        return http_json(API + caminho + "?" + urllib.parse.urlencode(params, doseq=True), corpo=corpo, ritmo=RITMO["itad"])
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ChaveRecusada("a IsThereAnyDeal recusou a chave (%s)" % explicar(e))
        raise


def norm(nome):
    return re.sub(r"[^a-z0-9]", "", (nome or "").lower())


def lojas(chave, pais):
    """[{id, title}] das lojas que a ITAD acompanha no pais."""
    return _get("service/shops/v1", chave, country=pais) or []


def resolver_lojas(chave, pais, nomes):
    todas = lojas(chave, pais)
    por_nome = {norm(s.get("title")): s for s in todas}
    achadas, faltando = {}, []
    for n in nomes:
        s = por_nome.get(norm(n))
        if not s:  # aceita prefixo: "Hype" acha "Hype Games"
            s = next((v for k, v in por_nome.items() if k.startswith(norm(n)) or norm(n).startswith(k)), None)
        if s:
            achadas[int(s["id"])] = s["title"]
        else:
            faltando.append(n)
    return achadas, faltando, todas


def mapear(chave, appids, cache, log=print):
    faltando = [a for a in appids if str(a) not in cache]
    for lote in lotes(faltando, 200):
        r = _post("lookup/id/shop/%d/v1" % SHOP_STEAM, chave, ["app/%d" % a for a in lote]) or {}
        for k, v in r.items():
            cache[k.split("/")[-1]] = v
        for a in lote:
            cache.setdefault(str(a), None)
    return {a: cache[str(a)] for a in appids if cache.get(str(a))}


def _drm_steam(deal):
    """A oferta da propria Steam vem com drm vazio; nas outras lojas, vazio = DRM desconhecido."""
    if (deal.get("shop") or {}).get("id") == SHOP_STEAM:
        return True
    return any("steam" in (d.get("name") or "").lower() for d in (deal.get("drm") or []))


def precos(chave, pais, gids, shop_ids, log=print):
    """{gid: {"ofertas": [...], "hist_all": centavos, "hist_y1": ..}} com TODAS as lojas pedidas,
    inclusive as que nao estao em promocao (nondeals) - assim sabemos quando a promo acaba."""
    from . import progresso
    saida = {}
    for n, lote in enumerate(lotes(gids, 200), 1):
        progresso.passo(min(n * 200, len(gids)), len(gids))
        try:
            r = _post("games/prices/v3", chave, lote, country=pais, shops=",".join(map(str, shop_ids)),
                      nondeals="true", vouchers="false") or []
        except ChaveRecusada:
            raise
        except Exception as e:
            log("   lote %d de precos ITAD falhou (%s), seguindo" % (n, e))
            continue
        for g in r:
            hl = g.get("historyLow") or {}
            ofertas = []
            for d in g.get("deals") or []:
                shop = d.get("shop") or {}
                ofertas.append({
                    "loja_id": shop.get("id"), "loja": shop.get("name"),
                    "preco": de_reais((d.get("price") or {}).get("amount")),
                    "cheio": de_reais((d.get("regular") or {}).get("amount")),
                    "corte": int(d.get("cut") or 0), "flag": d.get("flag"),
                    "menor_loja": de_reais((d.get("storeLow") or {}).get("amount")),
                    "drm_steam": _drm_steam(d), "drm": [x.get("name") for x in (d.get("drm") or [])],
                    "url": d.get("url"), "expira": d.get("expiry"),
                })
            # A mesma loja pode aparecer mais de uma vez (outra edicao, ex.: Nuuvem a R$ 34,87 e a R$ 299).
            # Fica uma por loja: a mais barata com DRM Steam, ou a mais barata de todas se nenhuma tiver.
            por_loja = {}
            for o in sorted((o for o in ofertas if o["preco"] is not None), key=lambda o: (not o["drm_steam"], o["preco"])):
                por_loja.setdefault(o["loja"], o)
            saida[g.get("id")] = {
                "ofertas": list(por_loja.values()),
                "hist_all": de_reais(((hl.get("all") or {}).get("amount"))),
                "hist_y1": de_reais(((hl.get("y1") or {}).get("amount"))),
            }
    return saida


def menores(chave, pais, gids, log=print):
    """Steam inteira (spec 07): {gid: {"flag", "hl", "hl1"}} em lotes de 200. flag e a marca da ITAD na oferta da
    Steam (N = novo recorde, H = igual ao recorde, S = menor da loja); hl/hl1 = menor de sempre e de 1 ano em todas as
    lojas da ITAD (centavos)."""
    saida = {}
    for n, lote in enumerate(lotes(gids, 200), 1):
        try:
            r = _post("games/prices/v3", chave, lote, country=pais, shops=str(SHOP_STEAM), vouchers="false") or []
        except ChaveRecusada:
            raise
        except Exception as e:   # quase sempre a cota (429): para aqui, quem ficou sem resposta tenta na proxima
            log("   menores da ITAD pararam no lote %d (%s)" % (n, explicar(e)))
            break
        for g in r:
            hl = g.get("historyLow") or {}
            st = next((d for d in g.get("deals") or [] if (d.get("shop") or {}).get("id") == SHOP_STEAM), {})
            saida[g.get("id")] = {"flag": st.get("flag"), "hl": de_reais((hl.get("all") or {}).get("amount")),
                                  "hl1": de_reais((hl.get("y1") or {}).get("amount"))}
    return saida


def historico(chave, pais, gid, shop_ids, dias, desde=None, tentativas=8):
    """[(loja, preco, cheio, corte, quando)] do log de precos da ITAD. desde (ISO): so o que veio depois.
    tentativas=1: no limite de ritmo (429) falha na hora em vez de esperar (a ITAD tem cota de ~100 chamadas em 5 min)."""
    desde = desde or (datetime.now(timezone.utc) - timedelta(days=dias)).replace(microsecond=0).isoformat()
    r = _get("games/history/v2", chave, tentativas=tentativas, id=gid, country=pais,
             shops=",".join(map(str, shop_ids)), since=desde) or []
    alvo = cambio.moeda_do_pais(pais)

    def valor(p):
        """O historico vem no dinheiro da loja (US$, EUR, GBP), nao em reais como os precos de agora: converte."""
        p = p or {}
        return de_reais(cambio.em_reais(p.get("amount"), p.get("currency"), alvo))

    out = []
    for e in r:
        deal = e.get("deal") or {}
        out.append(((e.get("shop") or {}).get("name"), valor(deal.get("price")), valor(deal.get("regular")),
                    int(deal.get("cut") or 0), e.get("timestamp")))
    return out
