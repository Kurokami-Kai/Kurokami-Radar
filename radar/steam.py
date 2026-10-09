"""Steam: lista de desejos, biblioteca, detalhes da loja, DLCs e opcoes de compra."""
import json
import os
import re
import urllib.error
import urllib.parse

from .rede import RITMO, centavos, http_json, lotes, servico_steam

API = "https://api.steampowered.com/"
CDN = "https://shared.fastly.steamstatic.com/store_item_assets/"
TIPOS = {0: "jogo", 1: "demo", 2: "mod", 3: "video", 4: "dlc", 6: "software", 11: "musica", 13: "ferramenta"}


def resolver_steamid(chave, perfil):
    """SteamID64 a partir do perfil. Tenta primeiro sem chave (perfil publico, XML da comunidade)."""
    import re
    import urllib.request
    perfil = str(perfil or "").strip().rstrip("/").split("/")[-1]
    if perfil.isdigit() and len(perfil) == 17:
        return perfil
    try:
        req = urllib.request.Request("https://steamcommunity.com/id/%s/?xml=1" % urllib.parse.quote(perfil),
                                     headers={"User-Agent": "KurokamiRadar/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            m = re.search(r"<steamID64>(\d{17})</steamID64>", r.read().decode("utf-8", "replace"))
        if m:
            return m.group(1)
    except Exception:
        pass
    if chave:
        r = http_json(API + "ISteamUser/ResolveVanityURL/v1/?" + urllib.parse.urlencode({"key": chave, "vanityurl": perfil}),
                      ritmo=RITMO["steam"])
        sid = ((r or {}).get("response") or {}).get("steamid")
        if sid:
            return sid
    raise RuntimeError("Nao consegui achar o SteamID de '%s'. Ponha o SteamID64 (17 digitos) em perfil_steam no config.json." % perfil)


def perfil_publico(steamid):
    """{"nome", "avatar"} do perfil (XML da comunidade, sem chave), para o icone no topo do painel. None se falhar."""
    import html
    import urllib.request
    try:
        req = urllib.request.Request("https://steamcommunity.com/profiles/%s/?xml=1" % int(steamid),
                                     headers={"User-Agent": "KurokamiRadar/0.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            x = r.read().decode("utf-8", "replace")
    except Exception:
        return None
    def campo(nome):
        m = re.search(r"<%s>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</%s>" % (nome, nome), x, re.S)
        return html.unescape(m.group(1).strip()) if m else None
    av = campo("avatarMedium") or campo("avatarIcon")
    if not av or not av.startswith("https://"):
        return None
    return {"nome": campo("steamID") or "", "avatar": av}


ULTIMA_PRIORIDADE = {}  # appid -> posicao na lista de desejos (0 = topo), da ultima leitura
ULTIMO_TEMPO = {}       # appid -> (minutos jogados, ultima vez em unix), da ultima leitura da biblioteca


def wishlist(chave, steamid):
    r = servico_steam(API + "IWishlistService/GetWishlist/v1/", {"steamid": str(steamid)}, None, RITMO["steam"])  # nao precisa de chave
    itens = [i for i in ((r or {}).get("response") or {}).get("items", []) if i.get("appid")]
    ULTIMA_PRIORIDADE.clear()
    for i in itens:
        if i.get("priority") is not None:
            ULTIMA_PRIORIDADE[int(i["appid"])] = int(i["priority"])
    return [int(i["appid"]) for i in itens]


def biblioteca_api(chave, steamid):
    url = API + "IPlayerService/GetOwnedGames/v1/?" + urllib.parse.urlencode(
        {"key": chave, "steamid": steamid, "include_played_free_games": 1, "skip_unvetted_apps": 0})
    r = http_json(url, ritmo=RITMO["steam"])
    jogos = ((r or {}).get("response") or {}).get("games", [])
    ULTIMO_TEMPO.clear()
    ULTIMO_TEMPO.update({int(g["appid"]): (g.get("playtime_forever") or 0, g.get("rtime_last_played") or None) for g in jogos})
    return [g["appid"] for g in jogos]


def conquistas(chave, steamid, appid):
    """Conquistas do jogo na conta (ficha, 1 chamada). Jogo sem conquistas: total 0. Perfil privado: erro 403."""
    try:
        r = http_json(API + "ISteamUserStats/GetPlayerAchievements/v1/?" + urllib.parse.urlencode(
            {"key": chave, "steamid": steamid, "appid": appid, "l": "brazilian"}), tentativas=2, timeout=15)
    except urllib.error.HTTPError as e:
        if e.code == 400 and "no stats" in (getattr(e, "corpo", "") or "").lower():
            return {"feitas": 0, "total": 0}
        raise
    cs = ((r or {}).get("playerstats") or {}).get("achievements") or []
    return {"feitas": sum(1 for c in cs if c.get("achieved")), "total": len(cs)}


def detalhes_loja(appid, pais):
    """O que a ficha mostra da pagina da loja (1 chamada, sem ritmo: e a pessoa abrindo a ficha, nunca em lote)."""
    r = http_json("https://store.steampowered.com/api/appdetails?" + urllib.parse.urlencode(
        {"appids": appid, "cc": pais, "l": "brazilian"}), tentativas=2, timeout=15)
    d = (r or {}).get(str(appid)) or {}
    if not d.get("success"):
        return {}
    d = d.get("data") or {}
    ss = d.get("screenshots") or []
    return {"descricao": d.get("short_description") or "", "captura": ss[0].get("path_full") if ss else None,
            "desenvolvedor": ", ".join(d.get("developers") or []), "editora": ", ".join(d.get("publishers") or []),
            "generos": ", ".join(g.get("description") for g in d.get("genres") or [] if g.get("description")),
            "conquistas": ((d.get("achievements") or {}).get("total")) or 0}


def ler_userdata(arquivo):
    try:
        with open(arquivo, encoding="utf-8-sig") as f:
            u = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {"wishlist": u.get("rgWishlist") or [], "possuidos": u.get("rgOwnedApps") or [],
            "carrinho": u.get("rgAppsInCart") or []}  # seguidos/ignorados: so em conta_steam.relacao


def url_asset(item, *campos):
    a = item.get("assets") or {}
    fmt = a.get("asset_url_format")
    for c in campos:
        if fmt and a.get(c):
            return CDN + fmt.replace("${FILENAME}", a[c])
    return None


EDICAO_COMPLETA = re.compile(r"deluxe|complete|completa|definitive|definitiva|ultimate|gold|ouro|goty|game of the year|"
                             r"premium|collector|colecionador|legendary|lend[aá]ria|anniversary|enhanced|royal|"
                             r"\+ ?season pass|bundle|cole[cç][aã]o|collection", re.I)


def _nome_norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("™", "").replace("®", ""))


def _edicoes(item):
    """Pacotes (edicoes) que vendem este app, sem os bundles."""
    out = []
    for o in [item.get("best_purchase_option")] + list(item.get("purchase_options") or []):
        if not isinstance(o, dict) or o.get("bundleid") or not o.get("packageid"):
            continue
        if any(e["packageid"] == o["packageid"] for e in out):
            continue
        final = centavos(o.get("final_price_in_cents"))
        if final is None:
            continue
        if final == 0 and not item.get("is_free"):
            continue  # pacote de R$ 0 num jogo pago = teste gratis / fim de semana gratis, nao e preco
        out.append({"packageid": int(o["packageid"]), "nome": o.get("purchase_option_name") or "",
                    "final": final, "cheio": centavos(o.get("original_price_in_cents")) or final,
                    "desconto": int(o.get("discount_pct") or 0), "conjunto": bool(o.get("must_purchase_as_set"))})
    return out


def _edicao_base(item, eds):
    """Qual pacote e 'o jogo'. Nao e o mais barato: o HITMAN WoA vende a 'Part One' a R$ 8,89,
    que e so um pedaco. Preferimos o pacote com o mesmo nome do app; depois, o que nao e edicao
    especial; por ultimo, o mais barato."""
    if not eds:
        return {}
    alvo = _nome_norm(item.get("name"))
    for e in eds:
        if _nome_norm(e["nome"]) == alvo:
            return e
    comuns = [e for e in eds if not EDICAO_COMPLETA.search(e["nome"]) and not e["conjunto"]]
    pool = comuns or eds
    # entre as comuns, a de maior preco cheio costuma ser o jogo inteiro (as menores sao "partes")
    return max(pool, key=lambda e: e["cheio"]) if len(pool) > 1 and _tem_partes(pool) else min(pool, key=lambda e: e["final"])


def _tem_partes(eds):
    return any(re.search(r"\bpart(e)? ?(one|um|1|i)\b|episode 1|epis[oó]dio 1|starter|standard access", e["nome"], re.I)
               for e in eds)


def get_items(ids, pais, extra=None, chave=None, por_lote=50, log=print):
    """ids: [{"appid":x}] / [{"bundleid":x}] / [{"packageid":x}]. Devolve a lista crua de store_items."""
    saida = []
    req = {"include_basic_info": True, "include_all_purchase_options": True, "include_release": True,
           "include_assets": True, "include_reviews": True}
    req.update(extra or {})
    from . import progresso
    total = len(ids)
    for n, lote in enumerate(lotes(ids, por_lote), 1):
        progresso.passo(min(n * por_lote, total), total)
        entrada = {"ids": lote, "context": {"language": "brazilian", "country_code": pais, "steam_realm": 1},
                   "data_request": req}
        try:
            r = servico_steam(API + "IStoreBrowseService/GetItems/v1/", entrada, chave, RITMO["steam"])
        except urllib.error.HTTPError as e:
            if e.code in (400, 414) and len(lote) > 1:
                meio = len(lote) // 2
                saida += get_items(lote[:meio], pais, extra, chave, por_lote, log)
                saida += get_items(lote[meio:], pais, extra, chave, por_lote, log)
                continue
            log("   lote %d recusado pela Steam (HTTP %d), seguindo" % (n, e.code))
            continue
        except Exception as e:
            log("   lote %d falhou (%s), seguindo" % (n, e))
            continue
        saida += [i for i in ((r or {}).get("response") or {}).get("store_items", []) if i.get("success") == 1]
    return saida


def normalizar_app(it):
    rv = ((it.get("reviews") or {}).get("summary_filtered")) or {}
    rel = it.get("release") or {}
    eds = _edicoes(it)
    base = _edicao_base(it, eds)
    final = base.get("final")
    cheio = base.get("cheio") or final
    gratis = bool(it.get("is_free"))
    if gratis and final is None:
        final = cheio = 0
    pai = ((it.get("related_items") or {}).get("parent_appid"))
    fim = None
    for o in [it.get("best_purchase_option")] + list(it.get("purchase_options") or []):
        for dsc in ((o or {}).get("active_discounts") or []) if isinstance(o, dict) else []:
            try:
                f = int(dsc.get("discount_end_date") or 0)
            except (TypeError, ValueError):
                f = 0
            if f and (fim is None or f < fim):
                fim = f
    for e in eds:
        e["papel"] = ("base" if e is base else
                      "completa" if EDICAO_COMPLETA.search(e["nome"]) else
                      "parcial" if base and e["cheio"] < base.get("cheio", 0) else "outra")
    return {
        "appid": int(it["appid"]), "nome": it.get("name"), "tipo": TIPOS.get(it.get("type"), "outro"),
        "pai": int(pai) if pai else None, "capa": url_asset(it, "header", "main_capsule"),
        "capa_v": url_asset(it, "library_capsule_2x", "library_capsule"),
        "fim_desconto": fim,
        "pacote": base.get("packageid"),
        "rpos": rv.get("percent_positive"), "rcount": rv.get("review_count"), "rotulo": rv.get("review_score_label"),
        "lancamento": rel.get("steam_release_date") or rel.get("original_release_date"),
        "em_breve": 1 if rel.get("is_coming_soon") else 0, "gratis": 1 if gratis else 0,
        "preco_steam": final, "cheio_steam": cheio, "desconto_steam": int(base.get("desconto") or 0),
        "franquia": "|".join(f.get("name") for f in ((it.get("basic_info") or {}).get("franchises") or [])
                             if isinstance(f, dict) and f.get("name")) or None,
        "_edicoes": eds,
        "_bundles": [int(o["bundleid"]) for o in (it.get("purchase_options") or [])
                     if isinstance(o, dict) and o.get("bundleid")],
    }


def _pacotes_uma_chamada(ids, pais):
    r = http_json("https://store.steampowered.com/api/packagedetails?" + urllib.parse.urlencode(
        {"packageids": ",".join(map(str, ids)), "cc": pais, "l": "brazilian"}), ritmo=RITMO["loja"])
    out = {}
    for k, d in (r or {}).items():
        if isinstance(d, dict) and d.get("success"):
            out[int(k)] = [int(a["id"]) for a in ((d.get("data") or {}).get("apps") or []) if a.get("id")]
    return out


def conteudo_pacotes(packageids, pais, log=print):
    """{packageid: [appids]} via packagedetails da loja - o unico lugar que lista as DLCs de uma edicao.
    Tenta varios pacotes por chamada; o que nao voltar no lote e pedido um a um."""
    out, ids = {}, list(packageids)
    lote_ok = True
    for lote in lotes(ids, 40):
        if lote_ok and len(lote) > 1:
            try:
                got = _pacotes_uma_chamada(lote, pais)
                out.update(got)
                if not got:
                    lote_ok = False  # a loja nao aceitou lote; segue um a um
            except Exception:
                lote_ok = False
        for pid in [p for p in lote if p not in out]:
            try:
                out.update(_pacotes_uma_chamada([pid], pais))
            except Exception as e:
                log("   conteudo do pacote %s falhou (%s)" % (pid, e))
    return out


def dlcs_pela_loja(appid, pais):
    """Plano B quando o GetDLCForApps recusa: appdetails da loja (1 jogo por chamada, limite ~200/5min)."""
    r = http_json("https://store.steampowered.com/api/appdetails?" + urllib.parse.urlencode(
        {"appids": appid, "cc": pais, "l": "brazilian", "filters": "basic"}), ritmo=RITMO["loja"])
    d = ((r or {}).get(str(appid)) or {})
    return [int(x) for x in ((d.get("data") or {}).get("dlc") or [])] if d.get("success") else []


def dlcs_dos_jogos(chave, steamid, appids, pais, log=print):
    """{appid_dlc: appid_pai} via GetDLCForApps (leitura tolerante, como no KurokamiPrecos)."""
    mapa = {}
    for lote in lotes(sorted(set(appids)), 100):
        entrada = {"steamid": str(steamid), "appids": [{"appid": int(a)} for a in lote],
                   "context": {"country_code": pais, "language": "brazilian"}}
        try:
            r = servico_steam(API + "IStoreBrowseService/GetDLCForApps/v1/", entrada, chave, RITMO["steam"])
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                log("   o GetDLCForApps e so para chaves de parceiro da Valve; uso a loja daqui pra frente")
                return None
            log("   lote de DLCs falhou (%s), seguindo" % e)
            continue
        conteudo = (r or {}).get("response") or {}
        blocos = next((conteudo[k] for k in ("dlc_data", "dlc", "app_dlc", "apps") if isinstance(conteudo.get(k), list)), None)
        if blocos is None:
            listas = [v for v in conteudo.values() if isinstance(v, list)]
            blocos = listas[0] if listas else []
        conhecidos = set(lote)
        for b in blocos:
            if not isinstance(b, dict):
                continue
            pai = b.get("appid") or b.get("parent_appid") or b.get("base_appid")
            try:
                pai = int(pai)
            except (TypeError, ValueError):
                continue
            for filho in _appids_em(b):
                if filho != pai and filho not in conhecidos:
                    mapa[filho] = pai
    return mapa


def _appids_em(no):
    achados = []
    if isinstance(no, dict):
        for k, v in no.items():
            if k in ("appid", "parent_appid", "base_appid"):
                continue
            achados += _appids_em(v)
            if k in ("dlcappid", "dlc_appid", "dlcid") and isinstance(v, int):
                achados.append(v)
    elif isinstance(no, list):
        for v in no:
            if isinstance(v, int):
                achados.append(v)
            else:
                if isinstance(v, dict) and isinstance(v.get("appid"), int):
                    achados.append(v["appid"])
                achados += _appids_em(v)
    return achados


def normalizar_opcao(it, tipo):
    """Bundle ou pacote (edicao) com a lista de apps que ele inclui."""
    apps = list(it.get("included_appids") or [])
    for inc in ((it.get("included_items") or {}).get("included_apps") or []):
        if inc.get("appid") and inc["appid"] not in apps:
            apps.append(inc["appid"])
    bpo = it.get("best_purchase_option") or {}
    final = centavos(bpo.get("final_price_in_cents"))
    oid = it.get("id") or it.get("bundleid") or it.get("packageid")
    return {
        "id": "%s:%s" % (tipo, oid), "tipo": tipo, "nome": it.get("name") or tipo,
        "final": final, "cheio": centavos(bpo.get("original_price_in_cents")) or final,
        "desconto": int(bpo.get("discount_pct") or 0),
        "desconto_bundle": int(bpo.get("bundle_discount_pct") or 0) if tipo == "bundle" else None,
        "itens": apps, "capa": url_asset(it, "header", "main_capsule"),
    }
