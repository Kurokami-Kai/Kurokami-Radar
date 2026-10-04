"""Medicoes da spec 04, Etapa 1.2 a 1.5, numa COPIA do banco real (apagada no fim); nada e gravado no banco.

Uso: py tools/medir_spec04.py [--banco CAMINHO] [--config CAMINHO]
1b filtros padrao de Promocoes e coluna "Costuma voltar"
1.2 vitrine (regra exclusiva selo > novo > igual > 24m) e avisos de uma rodada: regra atual x "so o Selo ligado"
1.3 userdata.json (so numeros)   1.4 DLCs em promocao   1.5 tempo/tamanho de painel.api_lista({})
Resultado bruto em dados/sonda/medir_spec04.json (fora do Git)."""
import argparse
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import analise, caminhos, config  # noqa: E402
from tools.backtest_selo import achar_banco  # noqa: E402

ORDEM = ["selo", "novo", "igual", "24m"]


def tipos_de(an):
    t = []
    if an.get("selo"):
        t.append("selo")
    pt = an.get("piso_tipo")
    t += {"novo": ["novo"], "raro": ["novo"], "igual": ["igual"], "24m": ["24m"]}.get(pt, [])
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    origem, cfg_arq = (args.banco, args.config) if args.banco else achar_banco()
    cfg_arq = args.config or cfg_arq
    raiz_real = os.path.dirname(os.path.dirname(origem))
    tmp = tempfile.mkdtemp(prefix="kr-spec04-")
    try:
        shutil.copy2(origem, os.path.join(tmp, "radar.sqlite3"))
        shutil.copy2(cfg_arq, os.path.join(tmp, "config.json"))
        caminhos.ARQ_BANCO = os.path.join(tmp, "radar.sqlite3")
        caminhos.ARQ_CONFIG = os.path.join(tmp, "config.json")
        caminhos.DADOS = caminhos.SONDA = os.path.join(tmp, "dados")
        res = medir(raiz_real)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(caminhos.BASE, "dados", "sonda"), exist_ok=True)
    with open(os.path.join(caminhos.BASE, "dados", "sonda", "medir_spec04.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


def medir(raiz_real):
    from radar import painel
    from radar.banco import Banco
    cfg = config.carregar()
    res = {"gerado": datetime.now(timezone.utc).isoformat()}
    dmin = cfg["alerta"].get("desconto_minimo", 0)

    # ---- 1.5 desempenho de /api/lista
    tempos = []
    for _ in range(3):
        t = time.perf_counter(); lista = painel.api_lista({}); tempos.append(time.perf_counter() - t)
    kb = len(json.dumps(lista, ensure_ascii=False).encode("utf-8")) / 1024
    res["1.5"] = {"mediana_s": round(statistics.median(tempos), 3), "tempos_s": [round(x, 3) for x in tempos],
                  "itens": len(lista["itens"]), "json_kb": round(kb, 1)}
    print("1.5 api_lista: mediana %.2f s (%s), %d itens, %.0f KB" % (
        res["1.5"]["mediana_s"], ", ".join("%.2f" % x for x in tempos), len(lista["itens"]), kb))

    b = Banco()
    ctx = analise.Contexto(b, cfg)

    # ---- 1.2 vitrine: um bloco por jogo (tipo_oferta), sem os que voce ja tem
    blocos = {"sem": dict.fromkeys(ORDEM, 0), "com": dict.fromkeys(ORDEM, 0)}
    for it in lista["itens"]:
        if it["appid"] in ctx.possuidos or not it["corte"]:
            continue
        t = tipos_de(it)
        if not t:
            continue
        blocos["sem"][t[0]] += 1
        if t[0] == "selo" or it["corte"] >= dmin:
            blocos["com"][t[0]] += 1
    res["1.2_vitrine"] = blocos
    print("1.2 vitrine sem desconto_minimo: %s | com desconto_minimo %d%%: %s" % (blocos["sem"], dmin, blocos["com"]))

    # ---- 1.2 avisos de uma rodada: regra atual x so o Selo ligado (favoritos avisam em qualquer tipo)
    of = {a: [dict(o, drm_steam=True) for o in l] for a, l in b.ofertas_atuais().items()}
    gg = {r["appid"]: dict(r) for r in b.q("SELECT * FROM gg")}
    marc = set(cfg["lojas"])
    atual = analise.avaliar(ctx, of, gg, marc)
    orig_an, orig_fav, orig_rok = analise.analisar, analise.favorito, analise.raridade_ok
    estado = {"fav": False}

    def fav_(j, al):
        estado["fav"] = orig_fav(j, al)
        return estado["fav"]

    def an_(*a, **k):
        an = orig_an(*a, **k)
        t = tipos_de(an)
        if "selo" in t or (estado["fav"] and t):
            an = dict(an, selo=True, selo_motivo=an["selo_motivo"] or "tipo " + t[0])
        else:
            an = dict(an, selo=False)
        return an
    analise.analisar, analise.favorito, analise.raridade_ok = an_, fav_, lambda *a: False
    try:
        so_selo = analise.avaliar(ctx, of, gg, marc)
    finally:
        analise.analisar, analise.favorito, analise.raridade_ok = orig_an, orig_fav, orig_rok
    A, S = {a["appid"]: a for a in atual}, {a["appid"]: a for a in so_selo}
    saem = [(A[x]["nome"], A[x].get("raridade"), A[x].get("selo"), A[x].get("favorito"), A[x]["corte"]) for x in A if x not in S]
    entram = [(S[x]["nome"], S[x].get("raridade"), S[x].get("favorito"), S[x]["corte"]) for x in S if x not in A]
    por_tag = lambda L: {k: sum(1 for a in L if (a.get("tag") if a.get("tag") in ("keyshop", "completo") else "oficial") == k)
                         for k in ("oficial", "keyshop", "completo")}
    res["1.2_avisos"] = {"atual": len(atual), "atual_por": por_tag(atual), "so_selo": len(so_selo),
                         "so_selo_por": por_tag(so_selo), "deixam": saem, "passam": entram}
    print("1.2 avisos: regra atual %d %s · só Selo %d %s" % (len(atual), por_tag(atual), len(so_selo), por_tag(so_selo)))
    print("    deixam de avisar (%d):" % len(saem))
    for n, r, s, f, c in sorted(saem, key=lambda x: x[0].lower()):
        print("      - %s (%s%s, -%d%%)" % (n, r, ", favorito" if f else "", c))
    print("    passam a avisar (%d):" % len(entram))
    for n, r, f, c in entram:
        print("      - %s (%s%s, -%d%%)" % (n, r, ", favorito" if f else "", c))

    # ---- 1.3 userdata.json (so numeros)
    caminhos.RAIZ_DADOS = raiz_real
    arq = caminhos.achar_userdata(cfg)
    ud = {"existe": bool(arq)}
    if arq:
        with open(arq, encoding="utf-8-sig") as f:
            u = json.load(f)
        ud["data"] = datetime.fromtimestamp(os.path.getmtime(arq), timezone.utc).isoformat(timespec="minutes")
        for k in ("rgFollowedApps", "rgIgnoredApps"):
            v = u.get(k)
            ids = {int(x) for x in (v.keys() if isinstance(v, dict) else v or [])}
            ud[k] = {"tem": k in u, "formato": type(v).__name__, "appids": len(ids), "na_lista": len(ids & ctx.lista)}
    res["1.3"] = ud
    print("1.3 userdata:", json.dumps(ud, ensure_ascii=False))

    # ---- 1.4 DLCs relevantes, nao possuidas, de jogos possuidos, com desconto agora
    dl = set()
    for pai in ctx.possuidos:
        if (ctx.jogos.get(pai) or {}).get("tipo") == "dlc":
            continue
        dl |= {d for d in ctx.relevantes(pai) if d not in ctx.possuidos}
    oa = b.ofertas_atuais(dl) if dl else {}
    itad = {r["appid"] for r in b.q("SELECT DISTINCT appid FROM oferta_atual WHERE corte>0")} & dl
    steam = {a for a in dl if (ctx.jogos.get(a) or {}).get("desconto_steam")}
    promo = {a for a in dl if any((o["corte"] or 0) > 0 for o in oa.get(a, []))}
    na_marc = {a for a in dl if any((o["corte"] or 0) > 0 and o["loja"] in marc for o in oa.get(a, []))}
    res["1.4"] = {"dlcs_relevantes_sem_ter": len(dl), "com_desconto": len(promo), "com_desconto_lojas_marcadas": len(na_marc),
                  "via_oferta_atual_itad": len(itad), "so_preco_steam_do_jogo": len(steam - itad)}
    print("1.4 DLCs:", json.dumps(res["1.4"], ensure_ascii=False))

    # ---- 1b: filtros padrao de Promocoes e coluna "Costuma voltar" (jogos da lista em promocao, sem os que voce tem)
    lojas_m = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")}
               if l.lower() in {x.lower() for x in cfg["lojas"]}]
    if "steam" in {x.lower() for x in cfg["lojas"]}:
        lojas_m.append("Steam (direto)")
    linhas = b.linhas_lote(lojas_m)
    promo = [it for it in lista["itens"] if it["corte"] and it["appid"] not in ctx.possuidos]
    somem = [it for it in promo if it["corte"] < 50 or (it["rcount"] or 0) < 5000]
    poucas = [it for it in promo if it["corte"] >= 50 and (it["rcount"] or 0) < 5000]
    dist, ex, antigos = {}, {}, 0
    for it in promo:
        txt, ordem = costuma_voltar(it, linhas.get(it["appid"], []))
        dist[txt] = dist.get(txt, 0) + 1
        ex.setdefault(txt, [])
        if len(ex[txt]) < 3:
            ri = it["rar_info"] or {}
            ex[txt].append("%s (-%d%%; %s)" % (it["nome"], it["corte"], dica(it)))
        if txt == "nunca teve esse desconto" and (it["rar_info"] or {}).get("ultima"):
            antigos += 1
    res["1b"] = {"em_promocao": len(promo), "somem_com_padrao": len(somem), "ficam_com_padrao": len(promo) - len(somem),
                 "corte50_rcount_menor_5000": len(poucas), "costuma_voltar": dist, "exemplos": ex,
                 "nunca_teve_mas_teve_antes_de_24m": antigos}
    print("1b em promoção (sem os que você tem): %d · somem com os filtros padrão: %d (ficam %d) · corte >= 50 com < 5.000 análises: %d"
          % (len(promo), len(somem), len(promo) - len(somem), len(poucas)))
    for txt, n in sorted(dist.items(), key=lambda x: -x[1]):
        print("   %-26s %4d  ex.: %s" % (txt, n, " | ".join(ex[txt])))
    print("   (\"nunca teve esse desconto\" que teve esse nível antes da janela de 24 meses: %d)" % antigos)
    b.con.close()
    return res


def costuma_voltar(it, linhas):
    """(texto, ordem) da coluna "Costuma voltar" (emenda 2 da spec 04). Ordem: menor = mais raro; None = fim."""
    ri = it.get("rar_info") or {}
    if not it.get("corte"):
        return None, None
    if ri.get("curto"):
        return "histórico curto", None
    eps = analise.episodios(analise.linha_do_tempo(linhas))
    ant = eps[:-1] if eps and eps[-1][1] >= time.time() - 1 else eps
    if not ant:
        return "primeira promoção", None
    if not ri.get("eps_nivel"):  # decisao de 04/10: "nunca" so se nao houve o nivel no historico inteiro
        return ("não teve nos últimos 2 anos", 0.5) if ri.get("ultima") else ("nunca teve esse desconto", 0)
    x = 12 / ri["por_ano"]
    if x < 1.5:
        txt = "todo mês"
    elif x < 10.5:
        txt = "a cada ~%d %s" % (round(x), "mês" if round(x) == 1 else "meses")
    elif x < 18:
        txt = "1 vez por ano"
    else:
        txt = "1 vez em 2 anos"
    return txt, ri["por_ano"]


def dica(it):
    ri = it.get("rar_info") or {}
    ult = ri.get("ultima")
    n = ri.get("eps_nivel") or 0
    return "nos últimos 2 anos: %d %s com -%d%% ou mais%s · maior desconto que já teve: -%s%%" % (
        n, "vez" if n == 1 else "vezes", max(0, it["corte"] - 5),
        " (última em %s/%s)" % (ult[5:7], ult[:4]) if ult else "", ri.get("corte_max"))


if __name__ == "__main__":
    main()
