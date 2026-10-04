"""Backtest por tipo de recorde (spec 04, Etapa 1.1): Selo, novo recorde, igual ao recorde e menor em 24 meses,
cada um medido sozinho, como se fosse a unica opcao de aviso ligada.

Uso: py tools/backtest_tipos.py [--banco CAMINHO] [--config CAMINHO] [--de 2022-10-06] [--ate 2025-10-02]
Le uma COPIA temporaria do banco (apagada no fim) e imprime so numeros agregados; o resultado bruto vai para
dados/sonda/backtest_tipos.json (fora do Git). Reaproveita as funcoes de tools/backtest_selo.py.

Evento = episodio (appid, inicio) na primeira semana em que aparece, decidido nessa semana (como no backtest do
Selo). A coluna "ev.qq" conta o episodio se ele entrar na variante em QUALQUER semana dele (so para comparar).
Metricas:
  nmb R$      : nos 12 meses seguintes nenhum preco nas lojas marcadas < preco do evento - R$ 0,10 e < 99% dele
                (o resto do mesmo episodio conta); e a metrica que o usuario vai ver
  nbat+5/+10  : sem corte >= corte do evento + 5 (+10) em 12 meses (backtest do Selo)
  nvolt6m     : o mesmo nivel de corte (+-5) nao voltou em 6 meses
  novos/sem   : mediana de eventos novos por semana, semanas normais / de grande promocao
  estoque     : mediana de episodios marcados ativos por semana normal (o "por semana" do backtest do Selo)
  hoje        : jogos na variante agora"""
import argparse
import bisect
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import analise, caminhos  # noqa: E402
from radar.analise import episodios, linha_do_tempo  # noqa: E402
from radar.banco import Banco  # noqa: E402
from tools.backtest_selo import ANO, DIA, achar_banco, grande_promo, ler_config  # noqa: E402

TIPOS = {"selo": lambda r: r["selo"], "novo": lambda r: r["piso_tipo"] in ("novo", "raro"),
         "igual": lambda r: r["piso_tipo"] == "igual", "24m": lambda r: r["piso_tipo"] == "24m",
         "todas": lambda r: True}


def variantes(dmin):
    """[(nome, tipo, corte minimo)]: selo so com selo_corte_minimo (ja dentro de r["selo"])."""
    out = [("selo", "selo", 0)]
    for t in ("novo", "igual", "24m"):
        out += [("%s >=0" % t, t, 0), ("%s >=%d" % (t, dmin), t, dmin)]
    return out + [("base: toda promocao", "todas", 0)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    ap.add_argument("--de", default="2022-10-06"); ap.add_argument("--ate", default="2025-10-02")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    origem, cfg_arq = (args.banco, args.config) if args.banco else achar_banco()
    tmp = tempfile.mkdtemp(prefix="kr-backtest-")
    try:
        copia = os.path.join(tmp, "radar.sqlite3")
        shutil.copy2(origem, copia)
        rodar(Banco(copia), *ler_config(cfg_arq or args.config), args)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def rodar(b, marc, dmin, args):
    lojas_m = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")}
               if l.lower() in marc] + (["Steam (direto)"] if "steam" in marc else [])
    jogos = {r["appid"] for r in b.q("SELECT appid FROM jogo WHERE na_lista=1 AND possuido=0")}
    linhas = {a: rs for a, rs in b.linhas_lote(lojas_m).items() if a in jogos}
    b.con.close()
    quandos = {a: [r["quando"] for r in rs] for a, rs in linhas.items()}
    agora = time.time()
    segs_full = {a: linha_do_tempo(rs, agora) for a, rs in linhas.items()}
    eps_full = {a: episodios(s) for a, s in segs_full.items()}
    de = datetime.fromisoformat(args.de).replace(hour=20, tzinfo=timezone.utc)
    ate = datetime.fromisoformat(args.ate).replace(hour=20, tzinfo=timezone.utc)
    semanas, t = [], de
    while t.timestamp() < agora:
        semanas.append(t); t += timedelta(days=7)
    semanas.append(datetime.fromtimestamp(agora, timezone.utc))  # "hoje"

    VAR = variantes(dmin)
    nomes = [v[0] for v in VAR]
    decisao = {v: {} for v in nomes}       # (appid, inicio) -> aceito na 1a semana em que apareceu?
    qualquer = {v: {} for v in nomes}      # episodio -> 1a semana em que entrou (qualquer semana dele)
    eventos = {v: [] for v in nomes}       # (appid, ts, corte, preco)
    novos = {v: [] for v in nomes}         # (semana, eventos novos)
    estoque = {v: [] for v in nomes}       # (semana, episodios marcados ativos)
    hoje = dict.fromkeys(nomes, 0)
    t0 = time.time()
    for i, w in enumerate(semanas):
        ts, lim = w.timestamp(), w.isoformat()
        ult = i == len(semanas) - 1
        n_novo, n_est = dict.fromkeys(nomes, 0), dict.fromkeys(nomes, 0)
        for a, rs in linhas.items():
            k = bisect.bisect_right(quandos[a], lim)
            if not k:
                continue
            sub = rs[:k]
            segs = linha_do_tempo(sub, ts)
            if not segs or segs[-1][2] is None or segs[-1][1] < ts - 1 or not segs[-1][3]:
                continue
            preco, corte = segs[-1][2], segs[-1][3]
            r = analise.analisar(sub, preco, corte, agora_=ts)
            chave = (a, r["inicio"] or lim)
            for nome, tipo, cmin in VAR:
                cand = bool(TIPOS[tipo](r)) and corte >= cmin
                if ult and cand:
                    hoje[nome] += 1
                if cand:
                    qualquer[nome].setdefault(chave, ts)
                if chave not in decisao[nome]:
                    decisao[nome][chave] = cand
                    if cand:
                        n_novo[nome] += 1
                        if ts <= ate.timestamp():
                            eventos[nome].append((a, ts, corte, preco))
                if decisao[nome][chave]:
                    n_est[nome] += 1
        if not ult:
            for v in nomes:
                novos[v].append((w, n_novo[v])); estoque[v].append((w, n_est[v]))
    print("(%d jogos, %d semanas, %.0fs, lojas: %s, desconto_minimo %d)" % (
        len(linhas), len(semanas) - 1, time.time() - t0, ", ".join(sorted(lojas_m)), dmin))

    def futuro(a, ts, dias):
        eps = eps_full.get(a, [])
        atual = next((e for e in eps if e[0] <= ts + 1 and e[1] >= ts - 1), None)
        fim = max(atual[1] if atual else ts, ts)
        return [e for e in eps if fim < e[0] <= ts + dias * DIA]

    def mais_barato(a, ts, p):
        lim = min(p - 10, p * 0.99)
        return any(s[2] is not None and s[2] < lim and s[1] > ts and s[0] <= ts + ANO for s in segs_full.get(a, []))

    def med(pares, grande, f=statistics.median):
        return round(f([q for w, q in pares if w <= ate and grande_promo(w) == grande] or [0]), 1)

    linhas_out = []
    print("%-20s %6s %6s %7s %7s %7s %7s %9s %9s %7s %5s  %s" % (
        "variante", "ev", "ev.qq", "nmb R$", "nbat+5", "nbat+10", "nvolt6m", "novos n/g", "media n/g", "estoque", "hoje", "texto"))
    for nome in nomes:
        ev = eventos[nome]
        n = len(ev) or 1
        nmb = 100 * sum(not mais_barato(a, ts, p) for a, ts, c, p in ev) / n
        nb5 = 100 * sum(not any(e[2] >= c + 5 for e in futuro(a, ts, 365)) for a, ts, c, p in ev) / n
        nb10 = 100 * sum(not any(e[2] >= c + 10 for e in futuro(a, ts, 365)) for a, ts, c, p in ev) / n
        nv6 = 100 * sum(not any(abs(e[2] - c) <= 5 for e in futuro(a, ts, 182)) for a, ts, c, p in ev) / n
        ev_qq = sum(1 for t_ in qualquer[nome].values() if t_ <= ate.timestamp())
        nn, ng, est = med(novos[nome], False), med(novos[nome], True), med(estoque[nome], False)
        mn, mg = med(novos[nome], False, statistics.mean), med(novos[nome], True, statistics.mean)
        texto = "em %d de 10 · ~%s/semana (%s em grandes promoções)" % (round(nmb / 10), _num(nn), _num(ng))
        print("%-20s %6d %6d %6.1f%% %6.1f%% %6.1f%% %6.1f%% %4s/%-4s %4s/%-4s %7s %5d  %s" % (
            nome, len(ev), ev_qq, nmb, nb5, nb10, nv6, _num(nn), _num(ng), _num(mn), _num(mg), _num(est), hoje[nome], texto))
        linhas_out.append({"variante": nome, "eventos": len(ev), "eventos_qualquer_semana": ev_qq,
                           "nao_ficou_mais_barato": round(nmb, 1), "nao_batido_5": round(nb5, 1),
                           "nao_batido_10": round(nb10, 1), "nao_voltou_6m": round(nv6, 1),
                           "novos_semana_normal": nn, "novos_semana_grande": ng,
                           "media_novos_normal": mn, "media_novos_grande": mg, "estoque_semana_normal": est,
                           "hoje": hoje[nome], "texto": texto})
    os.makedirs(caminhos.SONDA, exist_ok=True)
    with open(os.path.join(caminhos.SONDA, "backtest_tipos.json"), "w", encoding="utf-8") as f:
        json.dump({"gerado": datetime.now(timezone.utc).isoformat(), "de": args.de, "ate": args.ate,
                   "desconto_minimo": dmin, "jogos": len(linhas), "linhas": linhas_out}, f, ensure_ascii=False, indent=1)


def _num(x):
    return ("%g" % x).replace(".", ",")


if __name__ == "__main__":
    main()
