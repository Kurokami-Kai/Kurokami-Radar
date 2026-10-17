"""Status > Progresso > o ano jogo a jogo: o mesmo dado do Steam Replay (ISaleFeatureService/GetUserYearInReview, com a
chave da Steam do dono). A Steam so tem Replay a partir de 2022, e so de anos em que a conta jogou o bastante
("substantial"); o do ano corrente sai em dezembro.

Cache em `meta` "replay_<ano>": {"quando": iso UTC, "dado": compacto (ou None = a Steam nao tem esse ano)}. Ano passado
com dado nao muda mais (nunca vence); sem dado, ou o ano corrente, vence em 1 dia.
Com `farm_cartas` ligado, os jogos de farm (jogados.farmados) saem da lista, das horas, das sessoes e dos meses."""
from datetime import datetime, timezone

from . import jogados
from .rede import RITMO, http_json, servico_steam

URL = "https://api.steampowered.com/ISaleFeatureService/GetUserYearInReview/v1/"
PRIMEIRO_ANO = 2022


def baixar(chave, steamid, ano):
    """Replay de um ano, compacto; None se a Steam nao tem (ano fora, perfil privado, pouco jogado)."""
    import urllib.parse
    q = urllib.parse.urlencode({"key": chave, "steamid": str(steamid), "year": int(ano)})
    st = (((http_json(URL + "?" + q, ritmo=RITMO["steam"], tentativas=2, timeout=20) or {}).get("response") or {}).get("stats") or {})
    p = st.get("playtime_stats") or {}
    if not p.get("substantial") or not p.get("game_summary"):
        return None
    tot = int((p.get("total_stats") or {}).get("total_playtime_seconds") or 0)
    exato = {g["appid"]: int(g["stats"]["total_playtime_seconds"]) for g in p.get("games") or [] if g.get("stats")}
    jogos = [{"appid": g["appid"], "seg": exato.get(g["appid"], round(tot * (g.get("total_playtime_percentagex100") or 0) / 10000)),
              "sessoes": g.get("total_sessions") or 0, "novo": bool(g.get("new_this_year")), "demo": bool(g.get("demo") or g.get("playtest")),
              "primeira": g.get("rtime_first_played_lifetime")} for g in p["game_summary"]]
    meses = [{"t": m["rtime_month"], "seg": int((m.get("stats") or {}).get("total_playtime_seconds") or 0),
              "jogos": {str(g["appid"]): int((g.get("stats") or {}).get("total_playtime_seconds") or 0) for g in m.get("appid") or []}}
             for m in p.get("months") or []]
    sq = p.get("playtime_streak") or {}
    sm = p.get("summary_stats") or {}
    return {"seg": tot, "sessoes": (p.get("total_stats") or {}).get("total_sessions") or 0, "jogos": jogos, "meses": meses,
            "sequencia": {"dias": sq.get("longest_consecutive_days") or 0, "inicio": sq.get("rtime_start"),
                          "jogos": [g["appid"] for g in sq.get("streak_games") or []]},
            "conquistas": sm.get("total_achievements") or 0, "raras": sm.get("total_rare_achievements") or 0}


def _nomes_fora(b, appids):
    """Nome dos jogos do Replay que o Hunter nao conhece (demos, jogos que nao estao na conta): {appid: nome}."""
    conhecidos = {r["appid"] for r in b.q("SELECT appid FROM jogo WHERE nome IS NOT NULL AND appid IN (%s)" % ",".join(map(str, appids)))}
    fora = [a for a in appids if a not in conhecidos][:100]
    if not fora:
        return {}
    try:
        r = servico_steam("https://api.steampowered.com/IStoreBrowseService/GetItems/v1/",
                          {"ids": [{"appid": a} for a in fora], "context": {"language": "brazilian", "country_code": "BR", "steam_realm": 1}},
                          None, RITMO["steam"])
        return {str(i["appid"]): i["name"] for i in ((r or {}).get("response") or {}).get("store_items", []) if i.get("name")}
    except Exception:
        return {}


def _do_cache(b, ano, chave, steamid):
    agora = datetime.now(timezone.utc)
    c = b.meta("replay_%d" % ano)
    if c:
        idade = (agora - datetime.fromisoformat(c["quando"])).total_seconds()
        if (c["dado"] and ano < agora.year) or idade < 86400:
            return c["dado"]
    dado = baixar(chave, steamid, ano)
    if dado:
        dado["nomes"] = _nomes_fora(b, [g["appid"] for g in dado["jogos"]])
    b.meta("replay_%d" % ano, {"quando": agora.isoformat(), "dado": dado})
    b.commit()
    return dado


def do_ano(b, ano, chave, farm):
    """O que a aba mostra: {"ok", "motivo"?, "jogos": [...], "meses": [...], ...}, sem os jogos de farm."""
    if ano < PRIMEIRO_ANO:
        return {"ano": ano, "ok": False, "motivo": "A Steam só tem o Replay a partir de 2022."}
    if ano > datetime.now(timezone.utc).year:
        return {"ano": ano, "ok": False, "motivo": "Esse ano ainda não chegou."}
    sid = b.meta("steamid")
    if not chave or not sid:
        return {"ano": ano, "ok": False, "motivo": "Precisa da chave da Steam e do perfil em Configurações."}
    d = _do_cache(b, ano, chave, sid)
    if not d:
        return {"ano": ano, "ok": False, "motivo": "A Steam ainda não fechou o Replay deste ano (sai em dezembro)."
                if ano == datetime.now(timezone.utc).year else "A Steam não tem o Replay de %d desta conta (ano com pouco jogo ou perfil privado)." % ano}
    fora = jogados.farmados(b) if farm else set()
    tirados = [g for g in d["jogos"] if g["appid"] in fora]
    jogos = [g for g in d["jogos"] if g["appid"] not in fora]
    seg = sum(g["seg"] for g in jogos)
    nomes = {r["appid"]: (r["nome"], r["capa"]) for r in b.q(
        "SELECT appid, nome, capa FROM jogo WHERE appid IN (%s)" % ",".join(str(g["appid"]) for g in jogos))} if jogos else {}
    for g in jogos:
        n, g["capa"] = nomes.get(g["appid"]) or (None, None)
        g["nome"] = n or (d.get("nomes") or {}).get(str(g["appid"]))
    meses = [{"t": m["t"], "seg": sum(s for a, s in m["jogos"].items() if int(a) not in fora) if fora else m["seg"],
              "jogos": {a: s for a, s in m["jogos"].items() if int(a) not in fora}} for m in d["meses"]]
    sq = d["sequencia"] if not fora or not d["sequencia"]["jogos"] or any(a not in fora for a in d["sequencia"]["jogos"]) else {"dias": 0}
    return {"ano": ano, "ok": True, "seg": seg, "sessoes": d["sessoes"] - sum(g["sessoes"] for g in tirados),
            "jogos": sorted(jogos, key=lambda g: -g["seg"]), "meses": meses, "sequencia": sq,
            "conquistas": d["conquistas"], "raras": d["raras"], "steamid": str(sid),
            "farm": {"n": len(tirados), "seg": sum(g["seg"] for g in tirados)}}

