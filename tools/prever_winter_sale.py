"""Previsao do preco de cada jogo da lista de desejos na proxima Winter Sale da Steam (so leitura do banco).

Regra: o corte da Winter Sale = o maior corte da Steam nos ultimos 6 meses (sem promocao em 6 meses, nos 12).
Backtest nos invernos de 2023, 2024 e 2025 (so com o historico conhecido em 2 de novembro de cada ano) e a
confianca de cada previsao saem dos mesmos dados. Gera um HTML unico em dados/ (fora do Git).

Uso: py tools/prever_winter_sale.py [banco.sqlite3] [saida.html]
"""
import bisect
import collections
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.expandvars(r"%LOCALAPPDATA%\Kurokami Radar")
BANCO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DADOS, "dados", "radar.sqlite3")
SAIDA = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "dados", "previsao-winter-sale-2026.html")
ANO = 2026                                    # a Winter Sale que comeca em dezembro desse ano
INICIO_SALE, FIM_SALE = "17/12/2026", "04/01/2027"   # Steamworks: 17/12/2026 a 04/01/2027
LOJAS_SEM_STEAM = ("GOG", "Epic Game Store", "Microsoft Store", "Ubisoft Store", "EA Store", "Blizzard", "ZOOM Platform")
AGORA = datetime.now(timezone.utc)
UTC = timezone.utc


def dt(y, m, d):
    return datetime(y, m, d, tzinfo=UTC)


def inverno(y):
    """Janela comum a todos os invernos (a venda cobriu 22/12 a 02/01 em todos)."""
    return dt(y, 12, 22), dt(y + 1, 1, 2)


def estado(rows, t, ts):
    i = bisect.bisect_right(ts, t) - 1
    return rows[i] if i >= 0 else None


def janela(rows, a, b):
    ts = [r[0] for r in rows]
    out = []
    e = estado(rows, a, ts)
    if e:
        out.append(e)
    out += [r for r in rows if a < r[0] <= b]
    return out


def corte(r):
    """Corte do registro; brinde (preco 0 / -100%) nao conta como promocao."""
    return r[3] if r[1] > 0 and r[3] < 100 else 0


def corte_max(rows, a, b):
    js = janela(rows, a, b)
    return max(corte(r) for r in js) if js else None


def episodios(rows, a, b):
    """(pico de corte, preco cheio no pico) de cada episodio de promocao (corte > 0 seguido) que toca [a, b]."""
    eps, cur = [], None
    for r in janela(rows, a, b):
        if corte(r) > 0:
            if cur is None or corte(r) > cur[0]:
                cur = (corte(r), r[2])
        elif cur:
            eps.append(cur)
            cur = None
    if cur:
        eps.append(cur)
    return eps


def prever(rows, T, cheio=None):
    """(corte previsto, repeticoes do nivel, meses de historico, preco cheio mudou) com o que se sabia em T.
    Prefere os episodios feitos sobre o preco cheio de T (+-3%); se so ha de um cheio antigo, usa-os e avisa."""
    cheio = cheio or estado(rows, T, [r[0] for r in rows])[2]   # hoje: o cheio do jogo (o historico pode atrasar)
    e12 = episodios(rows, T - timedelta(days=365), T)
    e6 = episodios(rows, T - timedelta(days=183), T)
    atual = lambda es: [e for e in es if abs(e[1] - cheio) <= 0.03 * cheio]
    mudou = False
    if atual(e6) or atual(e12):
        e6, e12 = atual(e6), atual(e12)
    else:
        mudou = bool(e6 or e12)
    cortes = [e[0] for e in e12]
    pred = max(e[0] for e in e6) if e6 else (max(cortes) if cortes else 0)
    rep = sum(1 for c in cortes if abs(c - pred) <= 2.5) if pred else 0
    return pred, rep, (T - rows[0][0]).days / 30.4, mudou


def confianca(pred, rep, meses, mudou=False):
    """A = nivel repetido e 18+ meses de historico; B = nivel visto 1 vez ou preco cheio mudou; C = jogo novo (<18 meses) ou sem dado."""
    if meses < 18:
        return "C"
    if pred == 0 or (rep >= 2 and not mudou):
        return "A"
    return "B"


def brl(c):
    return ("R$ %.2f" % (c / 100)).replace(".", ",")


def preco_steam(cheio, corte):
    """Preco da Steam BR: termina em 9 (R$ 29,99 x 50% = R$ 14,99)."""
    p = cheio * (100 - corte) / 100
    return int((p + 1) // 10 * 10 - 1) if corte else int(cheio)


def carregar(con):
    jogos = {}
    for r in con.execute("SELECT appid,nome,tipo,preco_steam,cheio_steam,desconto_steam,prioridade,em_breve,gratis,rcount,rpos,rotulo,lancamento "
                         "FROM jogo WHERE na_lista=1"):
        jogos[r[0]] = dict(ap=r[0], nome=r[1], tipo=r[2], p=r[3], ch=r[4], co=r[5] or 0, pri=r[6] or 0, breve=r[7], gratis=r[8],
                           rc=r[9], rp=r[10], rot=r[11], lanc=r[12])
    S = {}
    for a, q, pr, ch, co in con.execute("SELECT appid,quando,preco,cheio,corte FROM preco WHERE loja='Steam' ORDER BY appid,quando"):
        if a in jogos:
            l = S.setdefault(a, [])
            if l and l[-1][1] == pr and l[-1][2] == ch:
                continue
            l.append((datetime.fromisoformat(q), pr, ch, co))
    return jogos, S


def menores(con, jogos, lojas):
    """Menor preco de todos os tempos (nas lojas marcadas, so as que vendem chave Steam) e o menor na Steam."""
    ids = ",".join(str(a) for a in jogos)
    ls = ",".join("'%s'" % l.replace("'", "''") for l in lojas)
    geral = {}
    for a, loja, pr, q in con.execute("SELECT appid,loja,preco,quando FROM preco WHERE appid IN (%s) AND loja IN (%s) "
                                      "AND fonte!='calculado' AND preco>0" % (ids, ls)):
        if a not in geral or pr < geral[a][0]:
            geral[a] = (pr, loja, q[:7])
    return geral


def backtest(S):
    """Acerto da regra nos invernos 2023-2025, por faixa de confianca."""
    R = []
    for y in (2023, 2024, 2025):
        T = dt(y, 11, 2)
        a, b = inverno(y)
        for ap, rows in S.items():
            if rows[0][0] > T - timedelta(days=60):
                continue
            alvo = corte_max(rows, a, b)
            if alvo is None:
                continue
            pred, rep, meses, mudou = prever(rows, T)
            R.append(dict(y=y, pred=pred, alvo=alvo, conf=confianca(pred, rep, meses, mudou)))

    def resumo(v):
        n = len(v)
        return dict(n=n, h25=sum(abs(x["pred"] - x["alvo"]) <= 2.5 for x in v) / n,
                    h5=sum(abs(x["pred"] - x["alvo"]) <= 5 for x in v) / n,
                    ao_menos=sum(x["alvo"] >= x["pred"] - 2.5 for x in v) / n,
                    alem=sum(x["alvo"] > x["pred"] + 5 for x in v) / n)
    out = {"todos": resumo(R)}
    for c in "ABC":
        out[c] = resumo([x for x in R if x["conf"] == c])
    out["anos"] = {y: resumo([x for x in R if x["y"] == y]) for y in (2023, 2024, 2025)}
    return out


def main():
    cfg = json.load(open(os.path.join(DADOS, "config.json"), encoding="utf-8"))
    lojas = [l for l in cfg.get("lojas", []) if not (cfg.get("somente_drm_steam") and l in LOJAS_SEM_STEAM)] or ["Steam"]
    con = sqlite3.connect("file:" + BANCO.replace("\\", "/") + "?mode=ro", uri=True)
    jogos, S = carregar(con)
    geral = menores(con, jogos, lojas)
    bt = backtest(S)
    linhas, sem = [], collections.Counter()
    for ap, j in jogos.items():
        rows = S.get(ap)
        if j["gratis"] or j["breve"] or not j["ch"]:
            sem["gratis ou ainda sem lançamento" if (j["gratis"] or j["breve"]) else "sem preço na Steam"] += 1
            continue
        if not rows:
            sem["sem histórico de preço"] += 1
            continue
        pred, rep, meses, mudou = prever(rows, AGORA, j["ch"])
        conf = confianca(pred, rep, meses, mudou)
        pp = preco_steam(j["ch"], pred)
        inv = []
        for y in range(2021, ANO):
            a, b = inverno(y)
            if rows[0][0] <= a:
                inv.append([y, corte_max(rows, a, b)])
        mins = min((r[1] for r in rows if r[1] > 0), default=None)
        g = geral.get(ap)
        menor = min(x for x in (mins, g[0] if g else None) if x) if (mins or g) else None
        loja_menor = "Steam" if (mins and (not g or mins <= g[0])) else (g[1] if g else "")
        quando = ""
        if menor:
            if loja_menor == "Steam":
                quando = max((r for r in rows if r[1] == menor), key=lambda r: r[0])[0].strftime("%Y-%m")
            else:
                quando = g[2]
        if pred == 0:
            ver = "sem"
        elif mudou:
            ver = "cheio"          # o menor preco antigo era de outro preco cheio: nao compara
        elif not menor:
            ver = "nd"
        else:
            tol = max(10, menor * 0.01)
            d = pp - menor
            ver = "novo" if d < -tol else "igual" if abs(d) <= tol else "perto" if d <= menor * 0.15 else "acima"
        linhas.append(dict(a=ap, n=j["nome"], t=j["tipo"], pri=j["pri"], h=j["p"], ch=j["ch"], hc=j["co"], pc=pred, pp=pp,
                           c=conf, mud=int(mudou), rep=rep, m=round(meses), v=ver, mn=menor, ml=loja_menor, mq=quando, inv=inv,
                           rc=j["rc"], rp=j["rp"]))
    meta = dict(gerado=AGORA.strftime("%d/%m/%Y"), inicio=INICIO_SALE, fim=FIM_SALE, lojas=len(lojas), bt=bt, sem=dict(sem),
                total=len(jogos))
    modelo = open(os.path.join(RAIZ, "tools", "prever_winter_sale.html"), encoding="utf-8").read()
    html = modelo.replace("/*DADOS*/", "const L=%s, M=%s;" % (json.dumps(linhas, ensure_ascii=False, separators=(",", ":")),
                                                            json.dumps(meta, ensure_ascii=False, separators=(",", ":"))))
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    open(SAIDA, "w", encoding="utf-8").write(html)
    print("ok:", SAIDA, "%d jogos com previsão, %d sem, %d KB" % (len(linhas), sum(sem.values()), len(html) // 1024))
    print("backtest:", {k: {a: round(b, 2) for a, b in v.items()} for k, v in bt.items() if k != "anos"})
    print(collections.Counter(l["v"] for l in linhas), collections.Counter(l["c"] for l in linhas))


if __name__ == "__main__":
    main()
