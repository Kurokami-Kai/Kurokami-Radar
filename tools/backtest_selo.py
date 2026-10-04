"""Backtest do Selo Kurokami: para cada semana, so com o historico conhecido ate aquela data, quem seria Selo?
Depois olha os meses seguintes (historico completo) e mede se o Selo "segurou".

Uso: py tools/backtest_selo.py [--banco CAMINHO] [--de 2022-10-06] [--ate 2025-10-02]
Le uma COPIA temporaria do banco (apagada no fim) e imprime so numeros agregados: nenhum dado vai para o repo.
Sem --banco usa o banco mais recente entre o da instalacao (%LOCALAPPDATA%) e o de dados/ (rodando pelo codigo).

Metricas por variante (cada Selo conta uma vez por episodio de promocao, na primeira semana em que aparece):
  nao batido +5 / +10 : nos 12 meses seguintes nao houve corte >= corte do Selo + 5 (ou + 10)
  nao voltou 6m       : nos 6 meses seguintes o mesmo nivel (+-5) nao voltou
  selos/semana        : mediana em semanas normais x semanas de grandes promocoes da Steam
  hoje                : episodios em promocao agora que a variante marcou (no dia em que comecaram)
Variantes: A atual (regra C) · B so com >= 24 meses de historico · C B + escada parada · D B + 1 Selo por jogo
a cada 12 meses (salvo corte 10+ pontos acima) · E B+C+D · F so Lendario · G pilula Recorde raro (regra
"rare deal" da SteamDB, em reais) · H qualquer novo recorde em reais (pilulas novo/raro) · F ou G · Selo atual (= G com
>= 1 promocao anterior e selo_corte_minimo 0, desde a 0.15; ate a 0.14 era F ou G) · alertas sem Selo (Raro/Ultrarraro com desconto_minimo do config). Linhas de base: toda promocao; toda
promocao no piso."""
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

DIA = 86400
ANO = 365 * DIA
VARIANTES = ["A", "B", "C", "D", "E", "F", "G", "H", "FouG", "Selo", "alerta_sem_selo", "todas", "no_piso"]
NOMES = {"A": "A Selo antigo (regra C)", "B": "B >= 24 meses", "C": "C B + escada parada", "D": "D B + 1 por jogo/12m",
         "E": "E B + C + D", "F": "F so Lendario",
         "G": "G Recorde raro (SteamDB)", "H": "H novo recorde em R$", "FouG": "F ou G (G sem promo ant.)",
         "Selo": "Selo atual (so G)", "alerta_sem_selo": "alertas sem Selo (Raro+)", "todas": "base: toda promocao", "no_piso": "base: toda promocao no piso"}


def grande_promo(dt):
    """Semanas aproximadas das grandes promocoes da Steam (primavera, verao, outono, inverno)."""
    md = (dt.month, dt.day)
    return ((3, 13) <= md <= (3, 23) or (6, 20) <= md <= (7, 13) or (11, 20) <= md <= (12, 4)
            or md >= (12, 18) or md <= (1, 6))


def achar_banco():
    inst = os.path.join(os.environ.get("LOCALAPPDATA") or "", "Kurokami Radar")
    cands = [(os.path.join(inst, "dados", "radar.sqlite3"), os.path.join(inst, "config.json")),
             (caminhos.ARQ_BANCO, caminhos.ARQ_CONFIG)]
    cands = [c for c in cands if os.path.isfile(c[0])]
    if not cands:
        sys.exit("Nenhum banco encontrado; use --banco")
    return max(cands, key=lambda c: os.path.getmtime(c[0]))


def ler_config(arq_config):
    """(lojas marcadas, desconto_minimo). So le; nunca cria/grava config."""
    from radar.config import PADRAO
    c = {}
    if arq_config and os.path.isfile(arq_config):
        with open(arq_config, encoding="utf-8-sig") as f:
            c = json.load(f)
    lojas = c.get("lojas") or PADRAO["lojas"]
    dmin = (c.get("alerta") or {}).get("desconto_minimo", PADRAO["alerta"]["desconto_minimo"])
    return {l.lower() for l in lojas}, dmin


def escada_parada(eps_ate, ts):
    """Sem o episodio atual: o maior corte dos ultimos 12 meses nao passou o dos 12 anteriores em mais de 5 pontos."""
    ant = [e for e in eps_ate if e[1] < ts - 1]
    m1 = max((e[2] for e in ant if e[0] > ts - ANO), default=0)
    m0 = max((e[2] for e in ant if ts - 2 * ANO < e[0] <= ts - ANO), default=0)
    return m1 <= m0 + 5


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    ap.add_argument("--de", default="2022-10-06"); ap.add_argument("--ate", default="2025-10-02")
    args = ap.parse_args()
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
    eps_full = {a: episodios(linha_do_tempo(rs, agora)) for a, rs in linhas.items()}
    de = datetime.fromisoformat(args.de).replace(hour=20, tzinfo=timezone.utc)
    ate = datetime.fromisoformat(args.ate).replace(hour=20, tzinfo=timezone.utc)
    semanas, t = [], de
    while t.timestamp() < agora:
        semanas.append(t); t += timedelta(days=7)
    semanas.append(datetime.fromtimestamp(agora, timezone.utc))  # "hoje"

    eventos = {v: [] for v in VARIANTES}          # (appid, ts, corte)
    decisao = {v: {} for v in VARIANTES}          # (appid, inicio) -> aceito?
    ultimo_selo = {v: {} for v in VARIANTES}      # appid -> (ts, corte) do ultimo Selo aceito (regra D)
    por_semana = {v: [] for v in VARIANTES}       # (data, quantos)
    t0 = time.time()
    for w in semanas:
        ts, lim = w.timestamp(), w.isoformat()
        conta = dict.fromkeys(VARIANTES, 0)
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
            # regra antiga do Selo (antes de 04/10): no piso + Raro ou melhor + 12 meses; A-E partem dela
            velho = r["no_piso"] and r["nivel"] in ("raro", "ultrarraro", "lendario") and r["meses"] >= 12
            base = {"todas": True, "no_piso": r["no_piso"], "A": velho, "F": r["nivel"] == "lendario",
                    "Selo": r["selo"], "alerta_sem_selo": not r["selo"] and corte >= dmin
                    and r["nivel"] in ("raro", "ultrarraro", "lendario"),
                    "G": r["piso_tipo"] == "raro", "H": r["piso_tipo"] in ("novo", "raro"),
                    "FouG": r["nivel"] == "lendario" or r["piso_tipo"] == "raro"}
            b24 = velho and r["meses"] >= 24
            parada = escada_parada(episodios(segs), ts) if b24 else False
            base.update(B=b24, C=b24 and parada)
            chave = (a, r["inicio"] or lim)
            for v in VARIANTES:
                cand = base.get(v, b24 and (parada or v == "D"))  # D e E partem de B (E tambem exige C)
                if chave not in decisao[v]:
                    ok = bool(cand)
                    if ok and v in ("D", "E"):
                        u = ultimo_selo[v].get(a)
                        ok = u is None or ts - u[0] >= ANO or corte >= u[1] + 10
                    decisao[v][chave] = ok
                    if ok:
                        if v in ("D", "E"):
                            ultimo_selo[v][a] = (ts, corte)
                        if ts <= ate.timestamp():
                            eventos[v].append((a, ts, corte))
                if decisao[v][chave]:
                    conta[v] += 1
        for v in VARIANTES:
            por_semana[v].append((w, conta[v]))
    print("(%d jogos, %d semanas, %.0fs)" % (len(linhas), len(semanas) - 1, time.time() - t0))

    def futuro(a, ts, dias):
        eps = eps_full.get(a, [])
        atual = next((e for e in eps if e[0] <= ts + 1 and e[1] >= ts - 1), None)
        fim = max(atual[1] if atual else ts, ts)
        return [e for e in eps if fim < e[0] <= ts + dias * DIA]

    print("%-28s %7s %9s %9s %9s %13s %6s" % ("variante", "eventos", "nbat+5", "nbat+10", "nvolt6m", "sem. norm/gr", "hoje"))
    for v in VARIANTES:
        ev = eventos[v]
        n = len(ev) or 1
        nb5 = sum(not any(e[2] >= c + 5 for e in futuro(a, ts, 365)) for a, ts, c in ev)
        nb10 = sum(not any(e[2] >= c + 10 for e in futuro(a, ts, 365)) for a, ts, c in ev)
        nv6 = sum(not any(abs(e[2] - c) <= 5 for e in futuro(a, ts, 182)) for a, ts, c in ev)
        sem = [(w, q) for w, q in por_semana[v][:-1] if w <= ate]
        norm = statistics.median([q for w, q in sem if not grande_promo(w)] or [0])
        gr = statistics.median([q for w, q in sem if grande_promo(w)] or [0])
        print("%-28s %7d %8.1f%% %8.1f%% %8.1f%% %6s/%-6s %6d" % (
            NOMES[v], len(ev), 100 * nb5 / n, 100 * nb10 / n, 100 * nv6 / n, norm, gr, por_semana[v][-1][1]))


if __name__ == "__main__":
    main()
