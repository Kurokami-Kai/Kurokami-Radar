"""Regua da Steam (spec 04, Etapa 1c): o Radar x "so a loja Steam" nos recordes raros. So LE; nada vai para o banco.

Uso: py tools/regua_steam.py [--banco CAMINHO] [--config CAMINHO] [--itad] [--retratos A.json B.json]
  1   os 5 rare deals que a SteamDB mostrava em 04/10 (jogos fora da lista: historico da ITAD so em memoria, com --itad)
  2/3 "Selo da Steam" (regra G so com a Steam) e "Novo recorde na Steam" na lista de hoje x o Radar
  4   (--itad) storeLow do deals/v2 e games/storelow/v2 (menor por loja, com data), ate 5 chamadas
  5   (--retratos) quantos precos mudam entre dois retratos do IStoreQueryService e quanto isso ocupa no SQLite
O backtest "so Steam" e `py tools/backtest_tipos.py --so-steam`. Resultado bruto em dados/sonda/regua_steam.json."""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import analise, caminhos, config  # noqa: E402
from radar.analise import _igual, episodios, linha_do_tempo  # noqa: E402
from tools.backtest_selo import achar_banco  # noqa: E402

STEAM = ["Steam", "Steam (direto)"]
# nome, appid e o preco que a SteamDB mostrava em 04/10/2026 (centavos)
REGUA = [("Ori and the Will of the Wisps", 1057090, 1290), ("FINAL FANTASY XV WINDOWS EDITION", 637650, 3750),
         ("CrossCode", 368340, 1200), ("The Escapists", 298630, 459), ("WRC 7 FIA World Rally Championship", 621830, 239)]


def brl(c):
    return "-" if c is None else "R$ %s" % ("%.2f" % (c / 100)).replace(".", ",")


def dia(iso):
    return (iso or "")[:10] or "-"


def ler(linhas, preco, corte, agora):
    """analisar + o que a regra G olha: menor preco antes do episodio de preco atual (loja, valor, data), a ultima vez
    nesse nivel, promocao anterior e o 1o registro."""
    an = analise.analisar(linhas, preco, corte, agora_=agora)
    segs = linha_do_tempo(linhas, agora)
    eps = episodios(segs)
    ant = eps[:-1] if eps and eps[-1][1] >= agora - 1 else eps
    out = {"piso_tipo": an["piso_tipo"], "selo_atual": an["selo"], "g": an["piso_tipo"] == "raro" and bool(ant),
           "anteriores": len(ant), "primeiro": min((r["quando"] for r in linhas if r["preco"]), default=None),
           "ref": an["piso_ref"], "nivel": an["nivel"], "lojas_ref": [], "preco": preco}
    if an["piso_ref"]:  # as duas condicoes da regra G
        r_ = an["piso_ref"]
        out["meses_ultima"] = round((agora - analise._ts(r_["quando"])) / (30.4 * 86400), 1)
        out["limite50"] = r_["preco"] * 0.5
    if preco is not None and segs:
        ini = agora
        for s in reversed(segs):
            if s[2] is not None and _igual(s[2], preco):
                ini = s[0]
            else:
                break
        ref = an["piso_ref"]
        if ref:  # quem fez o menor preco antes do episodio atual
            lim = datetime.fromtimestamp(ini, timezone.utc).isoformat()
            achou = {}
            for r in linhas:
                if r["preco"] == ref["preco"] and r["quando"] < lim:
                    achou[r["loja"]] = max(achou.get(r["loja"], ""), r["quando"])
            out["lojas_ref"] = sorted(achou.items(), key=lambda x: x[1], reverse=True)
    return out


def txt_ref(x):
    ref = x["ref"]
    if not ref:
        return "sem menor anterior"
    lojas = ", ".join("%s em %s" % (l, dia(q)) for l, q in x["lojas_ref"][:3]) or "?"
    return "%s (%s); última vez nesse nível: %s" % (brl(ref["preco"]), lojas, dia(ref["quando"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    ap.add_argument("--itad", action="store_true", help="busca na ITAD o historico dos jogos fora da lista e o item 4")
    ap.add_argument("--retratos", nargs=2, metavar="ARQ")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    origem, cfg_arq = (a.banco, a.config) if a.banco else achar_banco()
    cfg_arq = a.config or cfg_arq
    tmp = tempfile.mkdtemp(prefix="kr-regua-")
    res = {"gerado": datetime.now(timezone.utc).isoformat()}
    try:
        shutil.copy2(origem, os.path.join(tmp, "radar.sqlite3"))
        shutil.copy2(cfg_arq, os.path.join(tmp, "config.json"))
        caminhos.ARQ_BANCO = os.path.join(tmp, "radar.sqlite3")
        caminhos.ARQ_CONFIG = os.path.join(tmp, "config.json")
        caminhos.DADOS = caminhos.SONDA = os.path.join(tmp, "dados")
        from radar.banco import Banco
        b = Banco()
        cfg = config.carregar()
        res["1"] = regua(b, cfg, a.itad)
        res["2_3"] = lista_hoje(b, cfg)
        if a.itad:
            res["4"] = storelow(cfg)
        if a.retratos:
            res["5"] = mudancas(*a.retratos)
        b.con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pasta = os.path.join(caminhos.BASE, "dados", "sonda")
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, "regua_steam.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)


def marcadas(b, cfg):
    m = {x.lower() for x in cfg["lojas"]}
    lojas = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")} if l.lower() in m]
    return lojas + (["Steam (direto)"] if "steam" in m else [])


def regua(b, cfg, usar_itad):
    agora = time.time()
    lojas_m = marcadas(b, cfg)
    atuais = b.ofertas_atuais([x[1] for x in REGUA])
    marc = {x.lower() for x in cfg["lojas"]}
    hist_itad = itad_historico(cfg, [x[1] for x in REGUA]) if usar_itad else {}
    out = []
    print("== 1. Os 5 rare deals da SteamDB (04/10)")
    for nome, appid, preco_sdb in REGUA:
        j = b.um("SELECT possuido, na_lista, preco_steam, desconto_steam FROM jogo WHERE appid=?", appid)
        linhas = b.linhas_lote(lojas_m, [appid]).get(appid, [])
        fonte = "banco"
        if not linhas and appid in hist_itad:
            linhas, fonte = [r for r in hist_itad[appid] if r["loja"].lower() in marc], "ITAD (em memória)"
        lin_s = [r for r in (b.linhas_lote(STEAM, [appid]).get(appid, []) or
                             [r for r in hist_itad.get(appid, []) if r["loja"] == "Steam"])]
        ofs = [o for o in atuais.get(appid, []) if o["loja"].lower() in marc and o["preco"] is not None]
        melhor = min(ofs, key=lambda o: o["preco"]) if ofs else None
        st = next((o for o in atuais.get(appid, []) if o["loja"] == "Steam"), None)
        m = ler(linhas, melhor and melhor["preco"], melhor and melhor["corte"], agora) if melhor else None
        s = ler(lin_s, st and st["preco"], st and st["corte"], agora) if st else None
        lin = {"nome": nome, "appid": appid, "possuido": j and j["possuido"], "na_lista": j and j["na_lista"],
               "historico": fonte, "registros_marcadas": len(linhas), "registros_steam": len(lin_s),
               "steamdb": preco_sdb, "marcadas": melhor and [melhor["loja"], melhor["preco"], melhor["corte"]],
               "steam": st and [st["preco"], st["corte"]], "radar": m, "so_steam": s}
        lin["por_que"] = por_que(lin)
        out.append(lin)
        print("\n%s (appid %d)%s · histórico: %s (%d registros nas marcadas, %d na Steam)" % (
            nome, appid, " · você já tem" if lin["possuido"] else "", fonte, len(linhas), len(lin_s)))
        print("  a) agora: marcadas %s · Steam %s (SteamDB %s)" % (
            "%s %s -%d%%" % (melhor["loja"], brl(melhor["preco"]), melhor["corte"]) if melhor else "-",
            "%s -%d%%" % (brl(st["preco"]), st["corte"]) if st else "-", brl(preco_sdb)))
        if m:
            print("  b) Radar: piso_tipo %s · Selo hoje (F ou G) %s · Selo só G %s" % (m["piso_tipo"], m["selo_atual"], m["g"]))
            print("  c) menor antes do episódio, marcadas: %s" % txt_ref(m))
        if s:
            print("  d) só Steam: %s → piso_tipo %s · Selo da Steam (G) %s" % (txt_ref(s), s["piso_tipo"], s["g"]))
        if m:
            print("  e) promoções anteriores nas marcadas: %d · 1º registro: %s" % (m["anteriores"], dia(m["primeiro"])))
        print("  → %s" % lin["por_que"])
    return out


def motivo_g(x):
    """Por que a regra G nao bate (ou bate) com esse historico."""
    ref = x["ref"]
    if not ref:
        return "sem menor preço anterior"
    if x["piso_tipo"] not in ("novo", "raro"):
        return "não é recorde: %s está acima do menor anterior %s (piso_tipo %s)" % (brl(x["preco"]), txt_ref(x), x["piso_tipo"])
    return "%s %s 50%% do menor anterior (limite %s) e o menor anterior %s esteve nesse nível há %s meses (%s 18)" % (
        brl(x["preco"]), "≤" if x["preco"] <= x["limite50"] else ">", brl(round(x["limite50"])), brl(ref["preco"]),
        str(x["meses_ultima"]).replace(".", ","), "≥" if x["meses_ultima"] >= 18 else "<")


def por_que(l):
    m, s = l["radar"], l["so_steam"]
    if not l["registros_marcadas"]:
        return "o Radar não tem histórico: você já tem o jogo e ele só coleta a lista de desejos" if l["possuido"] else             "sem histórico nas lojas marcadas"
    pre = "[você já tem o jogo: o Radar não coleta jogos possuídos; histórico da ITAD só para este teste] " if l["possuido"] else ""
    if not m or not s:
        return pre + "sem preço atual"
    if l["steamdb"] != (l["steam"] or [None])[0]:
        pre += "[a SteamDB mostra %s; a Steam vende esse preço noutro pacote, o Radar usa o pacote com o nome do jogo] " % brl(l["steamdb"])
    if m["g"]:
        return pre + "o Radar também dá recorde raro: " + motivo_g(m)
    if not m["anteriores"]:
        return pre + "sem promoção anterior nas lojas marcadas"
    if s["g"]:
        return pre + "só com a Steam daria (%s), mas nas lojas marcadas %s" % (motivo_g(s), motivo_g(m))
    return pre + "nem só com a Steam dá recorde raro: " + motivo_g(s)


def itad_historico(cfg, appids):
    """{appid: [linhas como as do banco]} da ITAD, para os jogos sem historico no banco. Nada e gravado."""
    from radar import credenciais, itad
    chave = credenciais.ler("itad")
    if not chave:
        print("sem chave da ITAD; pulando o historico em memoria")
        return {}
    mapa = itad.mapear(chave, appids, {})
    ids, _f, _t = itad.resolver_lojas(chave, cfg["pais"], cfg["lojas"])
    out = {}
    for a, gid in mapa.items():
        regs = itad.historico(chave, cfg["pais"], gid, list(ids), cfg["historico"]["importar_dias"])
        out[a] = sorted(({"loja": l, "preco": p, "cheio": c, "corte": k, "quando": analise._iso(analise._ts(q))}
                         for l, p, c, k, q in regs if p is not None and q), key=lambda r: r["quando"])
    return out


def lista_hoje(b, cfg):
    """2/3: Selo da Steam e Novo recorde na Steam na lista de hoje, contra o Radar (lojas marcadas)."""
    agora = time.time()
    lojas_m = marcadas(b, cfg)
    marc = {x.lower() for x in cfg["lojas"]}
    jogos = {r["appid"]: r["nome"] for r in b.q("SELECT appid, nome FROM jogo WHERE na_lista=1 AND possuido=0")}
    lin_m, lin_s = b.linhas_lote(lojas_m), b.linhas_lote(STEAM)
    atuais = b.ofertas_atuais()
    selo_s, novo_s = [], []
    for a, nome in jogos.items():
        st = next((o for o in atuais.get(a, []) if o["loja"] == "Steam" and o["corte"]), None)
        if not st:
            continue
        s = ler(lin_s.get(a, []), st["preco"], st["corte"], agora)
        if not (s["g"] or s["piso_tipo"] in ("novo", "raro")):
            continue
        ofs = [o for o in atuais.get(a, []) if o["loja"].lower() in marc and o["preco"] is not None and o["corte"]]
        melhor = min(ofs, key=lambda o: o["preco"])
        m = ler(lin_m.get(a, []), melhor["preco"], melhor["corte"], agora)
        item = {"nome": nome, "steam": st["preco"], "marcadas": [melhor["loja"], melhor["preco"]], "radar_piso": m["piso_tipo"],
                "radar_g": m["g"], "radar_selo_atual": m["selo_atual"], "impediu": None if m["g"] else txt_ref(m)}
        if s["g"]:
            selo_s.append(item)
        if s["piso_tipo"] in ("novo", "raro"):
            novo_s.append(dict(item, radar_novo=m["piso_tipo"] in ("novo", "raro")))
    print("\n== 2. Selo da Steam hoje (G só com a Steam): %d · também Selo G do Radar: %d" % (
        len(selo_s), sum(x["radar_g"] for x in selo_s)))
    for x in selo_s:
        print("   - %s: Steam %s · marcadas %s %s · Radar %s%s" % (
            x["nome"], brl(x["steam"]), x["marcadas"][0], brl(x["marcadas"][1]), x["radar_piso"],
            "" if x["radar_g"] else " · impediu: " + x["impediu"]))
    fora = [x for x in novo_s if not x["radar_novo"]]
    print("== 3. Novo recorde na Steam hoje: %d · não são Novo recorde do Radar: %d" % (len(novo_s), len(fora)))
    for x in fora:
        print("   - %s: Steam %s · marcadas %s %s · Radar %s · menor anterior nas marcadas: %s" % (
            x["nome"], brl(x["steam"]), x["marcadas"][0], brl(x["marcadas"][1]), x["radar_piso"], x["impediu"]))
    return {"selo_steam": selo_s, "novo_steam": novo_s}


def storelow(cfg):
    """4: o deals/v2 traz storeLow? Com data? E o games/storelow/v2? (3 chamadas)"""
    from radar import credenciais, itad
    chave = credenciais.ler("itad")
    r = itad._get("deals/v2", chave, country=cfg["pais"], shops="61", limit=200) or {}
    lst = r.get("list") or []
    d0 = (lst[0].get("deal") or {}) if lst else {}
    com = sum(1 for it in lst if (it.get("deal") or {}).get("storeLow"))
    dif = sum(1 for it in lst if ((it.get("deal") or {}).get("storeLow") or {}).get("amountInt")
              != ((it.get("deal") or {}).get("historyLow") or {}).get("amountInt"))
    ids = [it["id"] for it in lst]
    sl = itad._post("games/storelow/v2", chave, ids, country=cfg["pais"], shops="61") or []
    s0 = (sl[0].get("lows") or [{}])[0] if sl else {}
    out = {"deals_itens": len(lst), "deals_storeLow_exemplo": d0.get("storeLow"), "deals_com_storeLow": com,
           "deals_storeLow_diferente_do_historyLow": dif, "storelow_jogos": len(sl), "storelow_exemplo": s0,
           "storelow_com_data": sum(1 for g in sl for x in g.get("lows") or [] if x.get("timestamp"))}
    print("\n== 4. ITAD: deals/v2 (só Steam) storeLow em %d de %d itens (ex.: %s; sem data) · diferente do historyLow em %d"
          % (com, len(lst), json.dumps(d0.get("storeLow")), dif))
    print("   games/storelow/v2: %d jogos numa chamada; exemplo: %s" % (len(sl), json.dumps(s0, ensure_ascii=False)))
    return out


def mudancas(arq_a, arq_b):
    """5: quantos precos mudam entre dois retratos e quanto isso ocupa no SQLite (tabela preco do Radar)."""
    def abrir(x):
        p = x if os.path.isabs(x) else os.path.join(caminhos.BASE, "dados", "sonda", x)
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    ra, rb = abrir(arq_a), abrir(arq_b)
    A, B = ra["precos"], rb["precos"]
    mud = sum(1 for k in A.keys() & B.keys() if A[k][:3] != B[k][:3])
    entram, saem = len(B.keys() - A.keys()), len(A.keys() - B.keys())
    horas = (datetime.fromisoformat(rb["quando"]) - datetime.fromisoformat(ra["quando"])).total_seconds() / 3600
    # bytes por registro: tabela preco + indice do Radar, com 100 mil registros parecidos com os da Steam
    tmp = tempfile.mkdtemp(prefix="kr-tam-")
    try:
        arq = os.path.join(tmp, "t.sqlite3")
        con = sqlite3.connect(arq)
        con.executescript("CREATE TABLE preco(appid INTEGER, loja TEXT, preco INTEGER, cheio INTEGER, corte INTEGER,"
                          " quando TEXT, fonte TEXT, url TEXT); CREATE INDEX preco_idx ON preco(appid, loja, quando);")
        q = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        con.executemany("INSERT INTO preco VALUES(?,?,?,?,?,?,?,NULL)",
                        ((int(k), "Steam (direto)", v[0] and int(v[0]), v[1] and int(v[1]), v[2], q, "steam_query")
                         for k, v in list(B.items())[:100000]))
        con.commit(); con.execute("VACUUM"); con.close()
        por_reg = os.path.getsize(arq) / min(100000, len(B))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = {"horas": round(horas, 2), "itens_a": len(A), "itens_b": len(B), "precos_mudaram": mud, "entraram": entram,
           "sairam": saem, "registros_novos": mud + entram + saem, "bytes_por_registro": round(por_reg)}
    print("\n== 5. Retratos com %.1f h de intervalo: %d → %d itens · mudaram %d · entraram %d · saíram %d · %d B por registro" % (
        horas, len(A), len(B), mud, entram, saem, por_reg))
    return out


if __name__ == "__main__":
    main()
