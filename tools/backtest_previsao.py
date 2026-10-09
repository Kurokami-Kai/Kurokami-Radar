"""Backtest da previsão de Ofertas (spec 09): "se eu não comprar agora, esse preço volta?" e "quando e por quanto
entra a próxima promoção?". Cada promoção da lista é um ponto de decisão, olhando só o histórico até aquele dia.

Uso: py tools/backtest_previsao.py [--banco CAMINHO] [--config CAMINHO]
Lê uma CÓPIA temporária do banco (apagada no fim) e imprime só números agregados; o detalhe vai para
dados/sonda/backtest_previsao.json (fora do Git).

Parte A (está em promoção a P): o preço P (ou menor, com a folga de centavos do "igual") volta em até 6/12 meses
depois que a promoção acaba? Modelos comparados por Brier, log loss e calibração:
  base   · taxa geral
  tipo   · taxa pelo tipo de preço (Selo, Novo recorde, Igual, Menor em 2 anos, nenhum)
  poisson· Gama-Poisson por jogo: k episódios anteriores a <= P em T dias de histórico, com uma prioridade
           ajustada pelos dados ((a + k) / (b + T) episódios por dia); P(volta em H) = 1 - ((b+T)/(b+T+H))^(a+k)
  pois24 · o mesmo, só com os últimos 24 meses (escada de descontos: o barato antigo pode não voltar)
  pois+tipo · Gama-Poisson com a prioridade por tipo de preço
Parte B (fora de promoção): data e preço da próxima promoção, por várias regras (último preço, mediana dos 3
últimos, mesmo evento do ano anterior, menor dos últimos 12 meses, tendência), medindo o erro. As regras de "mesmo
evento" supõem a data da próxima já conhecida (são um teto otimista, não um previsor completo).
Limites: as taxas por grupo são medidas na mesma amostra que avaliam (sem corte temporal); promoções de menos de
1 dia ficam de fora; --config só vale junto com --banco."""
import argparse
import bisect
import json
import math
import os
import shutil
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import analise, caminhos  # noqa: E402
from radar.analise import episodios, linha_do_tempo  # noqa: E402
from radar.banco import Banco  # noqa: E402

DIA = 86400.0
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_selo import achar_banco, ler_config  # noqa: E402


def tol(p):
    return max(10, p * 0.01)


def preco_ep(segs, e):
    v = [s[2] for s in segs if s[2] and s[0] < e[1] and s[1] > e[0] and s[3] > 0]
    return min(v) if v else None


def eventos_steam(segs_por_jogo):
    """Grandes eventos da Steam: dias em que 200+ jogos da lista começam promoção (vizinhos juntos)."""
    c = Counter()
    for segs in segs_por_jogo.values():
        for ini, _f, _c in episodios(segs):
            c[int(ini // DIA)] += 1
    ev = []
    for d in sorted(d for d, n in c.items() if n >= 200):
        if not ev or d - ev[-1] > 3:
            ev.append(d)
    return [d * DIA for d in ev]


def em_evento(t, ev, folga=4):
    return any(abs(t - e) <= folga * DIA for e in ev)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    args = ap.parse_args()
    origem, cfg_arq = (args.banco, args.config) if args.banco else achar_banco()
    tmp = tempfile.mkdtemp(prefix="kr-backtest-")
    try:
        copia = os.path.join(tmp, "radar.sqlite3")
        shutil.copy2(origem, copia)
        rodar(Banco(copia), *ler_config(cfg_arq or args.config))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- modelos da parte A
def gp(a, b, k, T, H):
    """Gama-Poisson: P(pelo menos 1 episódio a <= P em H dias)."""
    return 1 - ((b + T) / (b + T + H)) ** (a + k)


def ajustar(pontos, H, kf, Tf, grade_a=None, grade_b=None):
    """(a, b) que maximizam a verossimilhança (busca em grade)."""
    grade_a = grade_a or [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5, 8, 12, 20, 35, 60]
    grade_b = grade_b or [2, 5, 10, 20, 30, 60, 90, 180, 270, 365, 540, 730, 1095, 1460]
    melhor = None
    for a in grade_a:
        for b in grade_b:
            ll = 0.0
            for x in pontos:
                q = min(max(gp(a, b, kf(x), Tf(x), H), 1e-4), 1 - 1e-4)
                ll += math.log(q if x["y"][H] else 1 - q)
            if melhor is None or ll > melhor[0]:
                melhor = (ll, a, b)
    return melhor[1], melhor[2]


def medir(nome, pontos, H, prob):
    ps = [(min(max(prob(x), 1e-4), 1 - 1e-4), x["y"][H]) for x in pontos]
    brier = sum((p - y) ** 2 for p, y in ps) / len(ps)
    ll = -sum(math.log(p if y else 1 - p) for p, y in ps) / len(ps)
    acerto = sum((p >= 0.5) == bool(y) for p, y in ps) / len(ps)
    # calibração em 5 faixas de probabilidade prevista
    faixas = []
    for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]:
        f = [(p, y) for p, y in ps if lo <= p < hi]
        if f:
            faixas.append("%d-%d%%: prev %2.0f%% real %2.0f%% (n=%d)" % (
                lo * 100, min(hi, 1) * 100, 100 * sum(p for p, _ in f) / len(f), 100 * sum(y for _, y in f) / len(f), len(f)))
    print("  %-10s Brier %.3f  logloss %.3f  acerto %4.1f%%   | %s" % (nome, brier, ll, 100 * acerto, " · ".join(faixas)))
    return {"modelo": nome, "brier": round(brier, 4), "logloss": round(ll, 4), "acerto": round(100 * acerto, 1), "faixas": faixas}


def rodar(b, marc, _dmin):
    lojas_m = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")}
               if l.lower() in marc] + (["Steam (direto)"] if "steam" in marc else [])
    jogos = {r["appid"] for r in b.q("SELECT appid FROM jogo WHERE na_lista=1 AND possuido=0")}
    linhas = {a: rs for a, rs in b.linhas_lote(lojas_m).items() if a in jogos}
    steam = {a: rs for a, rs in b.linhas_lote(["Steam"]).items() if a in jogos}
    b.con.close()
    agora = time.time()
    t_ini = time.time()
    segs_full = {a: linha_do_tempo(rs, agora) for a, rs in linhas.items()}
    EV = eventos_steam({a: linha_do_tempo(rs, agora) for a, rs in steam.items()})
    print("(%d jogos; lojas: %s; %d grandes eventos da Steam detectados)" % (len(linhas), ", ".join(sorted(lojas_m)), len(EV)))
    quandos = {a: [r["quando"] for r in rs] for a, rs in linhas.items()}

    A, B = [], []
    for a, segs in segs_full.items():
        if not segs:
            continue
        t0 = segs[0][0]
        eps = episodios(segs)
        precos = [preco_ep(segs, e) for e in eps]
        for i, e in enumerate(eps):
            s_i, e_i = e[0], e[1]
            past = [(eps[j], precos[j]) for j in range(i) if eps[j][1] < s_i and precos[j]]
            # ---------------- parte B: prever o episódio i a partir do fim do anterior
            if i >= 1 and precos[i] and len(past) >= 2 and s_i - t0 >= 365 * DIA:
                tB = eps[i - 1][1] + DIA
                B.append({"a": a, "t": tB, "s": s_i, "p": precos[i], "past": past})
            # ---------------- parte A: decidir no 1º dia da promoção i
            t = s_i + DIA
            if t > e_i or t - t0 < 180 * DIA or e_i + 180 * DIA > agora:
                continue
            seg_t = next((s for s in segs if s[0] <= t < s[1]), None)
            if not seg_t or not seg_t[2] or not seg_t[3]:
                continue
            p, corte = seg_t[2], seg_t[3]
            lim = p + tol(p)
            ok_eps = [(pe, pp) for pe, pp in past if pp <= lim]
            ys = {}
            for H in (180, 365):
                fut = [s for s in segs if s[2] is not None and s[2] <= lim and s[0] >= e_i and s[0] <= e_i + H * DIA]
                ys[H] = 1 if fut else 0
                if H == 365:
                    espera = (fut[0][0] - e_i) / DIA if fut else None
            if e_i + 365 * DIA > agora:
                ys[365] = None
            k_rs = bisect.bisect_right(quandos[a], datetime.fromtimestamp(t, timezone.utc).isoformat())
            an = analise.analisar(linhas[a][:k_rs], p, corte, agora_=t)
            tipos = analise.tipos_de(an)
            A.append({"a": a, "t": t, "p": p, "corte": corte, "T": (t - t0) / DIA, "k": len(ok_eps),
                      "k24": sum(1 for pe, _ in ok_eps if pe[0] >= t - 730 * DIA),
                      "T24": min((t - t0) / DIA, 730), "tipo": analise.tipo_oferta(tipos) or "nenhum",
                      "volta": analise.costuma_voltar(an, corte)[0] or "",
                      "evento": em_evento(s_i, EV),
                      "y": ys, "espera": espera, "e_dur": (e_i - s_i) / DIA,
                      "gaps": [(ok_eps[j + 1][0][0] - ok_eps[j][0][0]) / DIA for j in range(len(ok_eps) - 1)]})
    print("(%.0fs) Parte A: %d promoções (decisão no 1º dia) · Parte B: %d próximas promoções\n" % (time.time() - t_ini, len(A), len(B)))
    out = {"gerado": datetime.now(timezone.utc).isoformat(), "jogos": len(linhas), "A": {}, "B": {}}

    # ================================================================ PARTE A
    for H in (180, 365):
        P = [x for x in A if x["y"][H] is not None]
        base = sum(x["y"][H] for x in P) / len(P)
        print("PARTE A · o preço de hoje (ou menor) volta em até %d meses depois do fim da promoção? n=%d, voltou %.1f%%" % (
            H // 30, len(P), 100 * base))
        por_tipo = defaultdict(list)
        for x in P:
            por_tipo[x["tipo"]].append(x["y"][H])
        taxa_tipo = {t: sum(v) / len(v) for t, v in por_tipo.items()}
        print("  por tipo: " + " · ".join("%s %.0f%% (n=%d)" % (t, 100 * taxa_tipo[t], len(por_tipo[t])) for t in
                                         ("selo", "novo", "igual", "24m", "nenhum") if t in taxa_tipo))
        por_volta = defaultdict(list)
        for x in P:
            por_volta[x["volta"] or "-"].append(x["y"][H])
        print("  por 'costuma voltar': " + " · ".join("%s %.0f%% (n=%d)" % (t, 100 * sum(v) / len(v), len(v))
                                                      for t, v in sorted(por_volta.items(), key=lambda kv: -len(kv[1]))[:10]))
        por_k = defaultdict(list)
        for x in P:
            por_k[min(x["k24"], 4)].append(x["y"][H])
        print("  por vezes a esse preço nos 24 meses anteriores: " + " · ".join(
            "%s %.0f%% (n=%d)" % ("4+" if k == 4 else k, 100 * sum(v) / len(v), len(v)) for k, v in sorted(por_k.items())))
        a1, b1 = ajustar(P, H, lambda x: x["k"], lambda x: x["T"])
        a2, b2 = ajustar(P, H, lambda x: x["k24"], lambda x: x["T24"])
        pri_tipo = {}
        for t in taxa_tipo:
            sub = [x for x in P if x["tipo"] == t]
            pri_tipo[t] = ajustar(sub, H, lambda x: x["k24"], lambda x: x["T24"]) if len(sub) >= 40 else (a2, b2)
        print("  prioridades: poisson a=%g b=%g · pois24 a=%g b=%g · por tipo %s" % (
            a1, b1, a2, b2, {t: v for t, v in pri_tipo.items()}))
        res = [medir("base", P, H, lambda x: base),
               medir("tipo", P, H, lambda x: taxa_tipo[x["tipo"]]),
               medir("poisson", P, H, lambda x: gp(a1, b1, x["k"], x["T"], H)),
               medir("pois24", P, H, lambda x: gp(a2, b2, x["k24"], x["T24"], H)),
               medir("pois+tipo", P, H, lambda x: gp(*pri_tipo[x["tipo"]], x["k24"], x["T24"], H))]
        out["A"][H] = {"n": len(P), "base": base, "tipo": taxa_tipo, "pois": [a1, b1], "pois24": [a2, b2],
                       "pois_tipo": pri_tipo, "modelos": res}
        print()

    # quanto demora a voltar, quando volta
    P = [x for x in A if x["y"][365]]
    w = sorted(x["espera"] for x in P)
    print("Quando volta (n=%d): espera mediana %.0f dias · 25%% em até %.0f · 75%% em até %.0f" % (
        len(w), statistics.median(w), w[len(w) // 4], w[3 * len(w) // 4]))
    for kk in (1, 2, 3):
        sub = [x for x in P if len(x["gaps"]) >= kk]
        if sub:
            err = [abs(x["espera"] + x["e_dur"] - statistics.median(x["gaps"])) for x in sub]
            print("  previsão 'intervalo mediano entre as vezes a esse preço' (>= %d intervalos, n=%d): erro mediano %.0f dias, %.0f%% em até 30 dias" % (
                kk, len(sub), statistics.median(err), 100 * sum(e <= 30 for e in err) / len(err)))
    print()

    # ---------------- A2: por grupo, em quanto tempo volta (espera depois do fim; > 365 = não voltou em 1 ano)
    P = [x for x in A if x["y"][365] is not None]
    for x in P:
        x["w"] = x["espera"] if x["y"][365] else 999
        x["kc"] = "0" if x["k24"] == 0 else "1" if x["k24"] == 1 else "2-3" if x["k24"] <= 3 else "4+"
    print("A2 · em quanto tempo o preço (ou menor) volta, por grupo (n; volta em 1 / 3 / 6 / 12 meses; espera mediana)")
    grupos = defaultdict(list)
    for x in P:
        grupos[(x["tipo"], x["kc"])].append(x["w"])
    out["A"]["grupos"] = {}
    for g in sorted(grupos, key=lambda g: (["selo", "novo", "igual", "24m", "nenhum"].index(g[0]), g[1])):
        w = sorted(grupos[g])
        if len(w) < 15:
            continue
        f = [sum(v <= d for v in w) / len(w) for d in (30, 90, 180, 365)]
        med = statistics.median(w)
        print("  %-7s vezes a esse preço em 24m: %-4s n=%5d · %3.0f%% / %3.0f%% / %3.0f%% / %3.0f%% · mediana %s" % (
            g[0], g[1], len(w), *[100 * v for v in f], ("%.0f dias" % med) if med < 999 else "> 1 ano"))
        out["A"]["grupos"]["%s|%s" % g] = {"n": len(w), "f30": f[0], "f90": f[1], "f180": f[2], "f365": f[3], "mediana": med}
    for rot, chave_f in (("costuma voltar", lambda x: x["volta"] or "-"),
                         ("corte", lambda x: "<40" if x["corte"] < 40 else "40-59" if x["corte"] < 60 else "60-74" if x["corte"] < 75 else "75-89" if x["corte"] < 90 else "90+"),
                         ("corte, só 1ª vez nesse preço", lambda x: None if x["k24"] else ("<60" if x["corte"] < 60 else "60-79" if x["corte"] < 80 else "80+")),
                         ("em grande evento da Steam", lambda x: "sim" if x["evento"] else "não")):
        gg = defaultdict(list)
        for x in P:
            c = chave_f(x)
            if c is not None:
                gg[c].append(x["w"])
        print("  por %s: " % rot + " · ".join("%s n=%d %.0f%%/%.0f%%" % (c, len(w), 100 * sum(v <= 30 for v in w) / len(w), 100 * sum(v <= 90 for v in w) / len(w))
                                           for c, w in sorted(gg.items(), key=lambda kv: -len(kv[1]))[:11] if len(w) >= 15) + "  (volta em 1 / 3 meses)")
    # 1ª vez nesse preço com corte de 80% ou mais (o grupo mais "raro" fora o Selo)
    w80 = sorted(x["w"] for x in P if not x["k24"] and x["corte"] >= 80)
    if w80:
        out["A"]["primeira80"] = {"n": len(w80), "f90": sum(v <= 90 for v in w80) / len(w80),
                                  "f365": sum(v <= 365 for v in w80) / len(w80), "mediana": statistics.median(w80)}
    # cada jogo com o mesmo peso (os jogos que vivem em promoção não dominam)
    pj = defaultdict(list)
    for x in P:
        pj[x["a"]].append(x["y"][365])
    print("  por jogo (cada jogo pesa igual): volta em 12 meses %.1f%% (%d jogos)" % (
        100 * statistics.mean(sum(v) / len(v) for v in pj.values()), len(pj)))

    # ---------------- A3: prever a espera
    def classe(d):
        return 0 if d <= 30 else 1 if d <= 90 else 2 if d <= 180 else 3 if d <= 365 else 4
    med_grupo = {g: statistics.median(w) for g, w in grupos.items()}

    def w_jogo(x):
        """Pelo próprio jogo: intervalo mediano entre as vezes a esse preço, menos a duração típica de uma promoção."""
        return max(0, statistics.median(x["gaps"][-6:]) - 10) if len(x["gaps"]) >= 1 else None

    def w_comb(x):
        v = w_jogo(x)
        return v if v is not None and x["k24"] >= 2 else med_grupo[(x["tipo"], x["kc"])]
    print("\nA3 · prever a espera (classe: até 1 mês, 1-3, 3-6, 6-12 meses, mais de 1 ano)")
    out["A"]["espera"] = {}
    for nome, f in (("mediana do grupo", lambda x: med_grupo[(x["tipo"], x["kc"])]), ("intervalo do próprio jogo", w_jogo),
                    ("jogo se 2+ vezes, senão grupo", w_comb)):
        pares = [(f(x), x["w"]) for x in P if f(x) is not None]
        ok = sum(classe(p) == classe(r) for p, r in pares) / len(pares)
        viz = sum(abs(classe(p) - classe(r)) <= 1 for p, r in pares) / len(pares)
        longo = [r for p, r in pares if p > 90]
        print("  %-30s n=%5d · classe certa %4.1f%% · no máximo 1 classe de erro %4.1f%% · previu > 3 meses: %d, e de fato demorou > 3 meses em %.0f%%" % (
            nome, len(pares), 100 * ok, 100 * viz, len(longo), 100 * sum(r > 90 for r in longo) / max(1, len(longo))))
        out["A"]["espera"][nome] = {"n": len(pares), "classe": ok, "viz": viz}
    print()

    # ================================================================ PARTE B
    def mesmo_evento(x):
        """Preço do episódio do ano anterior perto da mesma data (±25 dias), se houver."""
        alvo = x["s"] - 365 * DIA
        c = [pp for pe, pp in x["past"] if abs(pe[0] - alvo) <= 25 * DIA]
        return min(c) if c else None

    def tendencia(x):
        """Preço no mesmo evento do ano anterior × a variação entre os dois anos anteriores (escada), limitado."""
        c1 = mesmo_evento(x)
        if not c1:
            return None
        alvo2 = x["s"] - 730 * DIA
        c2 = [pp for pe, pp in x["past"] if abs(pe[0] - alvo2) <= 25 * DIA]
        if not c2:
            return c1
        r = c1 / min(c2)
        return c1 * min(1.0, max(0.7, r))

    def menor12(x):
        c = [pp for pe, pp in x["past"] if pe[0] >= x["t"] - 365 * DIA]
        return min(c) if c else None

    def med3(x):
        return statistics.median([pp for _pe, pp in x["past"][-3:]])

    def ultimo(x):
        return x["past"][-1][1]

    def combinada(x):
        """Mesmo evento do ano anterior (com tendência) se houver; senão a mediana dos 3 últimos."""
        return tendencia(x) or med3(x)

    def combinada2(x):
        """Mediana entre: mesmo evento (tendência), mediana dos 3 últimos e o menor de 12 meses."""
        c = [v for v in (tendencia(x), med3(x), menor12(x)) if v]
        return statistics.median(c)

    regras = [("último preço (anterior)", ultimo), ("mediana dos 3 últimos", med3), ("menor de 12 meses", menor12),
              ("mesmo evento ano ant.*", mesmo_evento), ("mesmo evento + tendência*", tendencia),
              ("evento+tend. ou mediana 3", combinada), ("mediana de três regras", combinada2)]
    print("PARTE B · preço da próxima promoção (n=%d; erro em %% do preço real; * = supõe a data já conhecida)" % len(B))
    out["B"]["preco"] = []
    for nome, f in regras:
        errs, igual = [], 0
        for x in B:
            v = f(x)
            if v is None:
                continue
            errs.append(abs(v - x["p"]) / x["p"])
            igual += abs(v - x["p"]) <= tol(x["p"])
        if errs:
            print("  %-28s cobre %4.0f%%  erro mediano %4.1f%%  em até 10%%: %4.1f%%  exato: %4.1f%%" % (
                nome, 100 * len(errs) / len(B), 100 * statistics.median(errs), 100 * sum(e <= .1 for e in errs) / len(errs),
                100 * igual / len(errs)))
            out["B"]["preco"].append({"regra": nome, "cobre": len(errs) / len(B), "erro_mediano": statistics.median(errs),
                                      "ate10": sum(e <= .1 for e in errs) / len(errs)})
    # confiança do último preço: quantas das 6 últimas tiveram esse mesmo preço (só jogos com 6+ promoções antes;
    # com menos, um balde à parte "poucas"); e a faixa das 3 últimas para quando elas variam
    print("\nPARTE B · o último preço, pela concordância (quantas das 6 últimas tiveram esse mesmo preço)")
    concU, faixa3 = defaultdict(list), []
    for x in B:
        ult = x["past"][-1][1]
        ult6 = [pp for _pe, pp in x["past"][-6:]]
        c = sum(abs(v - ult) <= tol(ult) for v in ult6) if len(ult6) == 6 else "poucas"
        concU[c].append(abs(ult - x["p"]) <= tol(x["p"]))
        u3 = [pp for _pe, pp in x["past"][-3:]]
        faixa3.append(min(u3) - tol(min(u3)) <= x["p"] <= max(u3) + tol(max(u3)))
    print("  " + " · ".join("%s n=%d: repetiu em %.0f%%" % ("%s/6" % c if c != "poucas" else "menos de 6 promoções", len(v), 100 * sum(v) / len(v))
                           for c, v in sorted(concU.items(), key=lambda kv: str(kv[0]))))
    print("  a próxima ficou entre o menor e o maior das 3 últimas em %.0f%%" % (100 * sum(faixa3) / max(1, len(faixa3))))
    out["B"]["concU"] = {str(c): sum(v) / len(v) for c, v in concU.items()}
    out["B"]["concU_n"] = {str(c): len(v) for c, v in concU.items()}
    out["B"]["faixa3"] = sum(faixa3) / max(1, len(faixa3))
    # data: intervalo mediano x próximo evento em que o jogo esteve no ano anterior
    print("\nPARTE B · data da próxima promoção (erro em dias)")
    errs = defaultdict(list)
    for x in B:
        starts = [pe[0] for pe, _ in x["past"]]
        gaps = [b_ - a_ for a_, b_ in zip(starts, starts[1:])]
        med = statistics.median(gaps[-6:])
        r1 = max(starts[-1] + med, x["t"])
        futuros = sorted(e + 364 * DIA for e in EV if x["t"] - 365 * DIA <= e < x["t"] and e + 364 * DIA > x["t"])
        esteve = [f for f in futuros if any(abs(pe[0] - (f - 364 * DIA)) <= 4 * DIA for pe, _ in x["past"])]
        r2 = (esteve or futuros or [r1])[0]
        share = sum(1 for pe, _ in x["past"][-6:] if em_evento(pe[0], EV)) / len(x["past"][-6:])
        r3 = r2 if share >= 0.6 else r1
        r4 = min(r1, r2)
        for nome, r in (("intervalo mediano", r1), ("próximo evento em que esteve", r2), ("evento se >=60% em eventos", r3),
                        ("o que vier antes", r4)):
            errs[nome].append(abs(r - x["s"]) / DIA)
    out["B"]["data"] = {}
    for nome, e in errs.items():
        print("  %-30s erro mediano %3.0f dias · em até 14 dias %4.1f%% · em até 30 %4.1f%%" % (
            nome, statistics.median(e), 100 * sum(v <= 14 for v in e) / len(e), 100 * sum(v <= 30 for v in e) / len(e)))
        out["B"]["data"][nome] = {"mediano": statistics.median(e), "ate14": sum(v <= 14 for v in e) / len(e),
                                  "ate30": sum(v <= 30 for v in e) / len(e)}
    os.makedirs(caminhos.SONDA, exist_ok=True)
    with open(os.path.join(caminhos.SONDA, "backtest_previsao.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
