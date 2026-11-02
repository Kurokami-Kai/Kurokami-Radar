"""Previsao do preco de cada jogo da lista de desejos na proxima Winter Sale da Steam (so leitura do banco).

Nao e uma previsao de um numero so: cada jogo recebe uma escada de cenarios (desconto -> preco -> chance de chegar
ao menos la) e a chance de bater o menor preco da historia. O ponto de partida e o maior corte da Steam nos ultimos
6 meses (sem promocao em 6 meses, nos 12); a distribuicao de quanto o inverno passa (ou fica abaixo) desse ponto vem
dos invernos de 2023, 2024 e 2025 (so com o historico conhecido em 2 de novembro de cada ano), por faixa de confianca.
A calibracao e conferida deixando um ano de fora. Gera um HTML unico em dados/ (fora do Git).

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
sys.path.insert(0, RAIZ)
from radar import series  # noqa: E402

DADOS = os.path.expandvars(r"%LOCALAPPDATA%\Kurokami Radar")
BANCO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DADOS, "dados", "radar.sqlite3")
SAIDA = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "dados", "previsao-winter-sale-2026.html")
ANO = 2026                                    # a Winter Sale que comeca em dezembro desse ano
INICIO_SALE, FIM_SALE = "17/12/2026", "04/01/2027"   # Steamworks: 17/12/2026 a 04/01/2027
ANOS_TESTE = (2023, 2024, 2025)               # 2022 fica de fora: so ha 13 meses de historico em nov/2022 (tudo parece recorde)
LOJAS_SEM_STEAM = ("GOG", "Epic Game Store", "Microsoft Store", "Ubisoft Store", "EA Store", "Blizzard", "ZOOM Platform")
DEGRAUS = [10, 15, 20, 25, 30, 33, 35, 40, 45, 50, 55, 60, 65, 67, 70, 75, 80, 85, 90]
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
    """A = nivel repetido e 18+ meses de historico; B = nivel visto 1 vez ou preco cheio mudou; C = jogo novo (<18 meses)."""
    if meses < 18:
        return "C"
    if pred == 0 or (rep >= 2 and not mudou):
        return "A"
    return "B"


def banda(p):
    return 0 if p == 0 else 1 if p <= 45 else 2 if p <= 69 else 3


PREFIXO_CAPA = "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"


def capa_curta(u):
    """Tira o prefixo da CDN (a pagina o recoloca); URL de outro lugar fica inteira."""
    return (u[len(PREFIXO_CAPA):] if u and u.startswith(PREFIXO_CAPA) else u) or ""


def preco_steam(cheio, c):
    """Preco da Steam BR: termina em 9 (R$ 29,99 x 50% = R$ 14,99)."""
    p = cheio * (100 - c) / 100
    return int((p + 1) // 10 * 10 - 1) if c else int(cheio)


def carregar(con):
    jogos = {}
    for r in con.execute("SELECT appid,nome,tipo,preco_steam,cheio_steam,desconto_steam,prioridade,em_breve,gratis,rcount,rpos,"
                         "lancamento,franquia,pai,capa_v,capa FROM jogo WHERE na_lista=1"):
        jogos[r[0]] = dict(ap=r[0], nome=r[1], tipo=r[2], p=r[3], ch=r[4], co=r[5] or 0, pri=r[6] or 0, breve=r[7], gratis=r[8],
                           rc=r[9], rp=r[10], lanc=r[11], franquia=r[12], pai=r[13], cv=r[14], hd=r[15])
    S = {}
    for a, q, pr, ch, co in con.execute("SELECT appid,quando,preco,cheio,corte FROM preco WHERE loja='Steam' ORDER BY appid,quando"):
        if a in jogos:
            l = S.setdefault(a, [])
            if l and l[-1][1] == pr and l[-1][2] == ch:
                continue
            l.append((datetime.fromisoformat(q), pr, ch, co))
    return jogos, S


def historico_lojas(con, jogos, lojas):
    """appid -> [(quando ISO, preco, loja)] nas lojas marcadas que vendem chave Steam (sem brindes nem 'calculado')."""
    ids = ",".join(str(a) for a in jogos)
    ls = ",".join("'%s'" % l.replace("'", "''") for l in lojas)
    H = collections.defaultdict(list)
    for a, loja, pr, q in con.execute("SELECT appid,loja,preco,quando FROM preco WHERE appid IN (%s) AND loja IN (%s) "
                                      "AND fonte!='calculado' AND preco>0 ORDER BY quando" % (ids, ls)):
        H[a].append((q, pr, loja))
    return H


def menor_ate(ap, T, S, H):
    """(menor preco, loja, 'AAAA-MM') ate T: Steam e lojas marcadas juntas."""
    iso = T.isoformat()
    melhor = None
    for q, pr, loja in H.get(ap, ()):
        if q <= iso and (melhor is None or pr < melhor[0]):
            melhor = (pr, loja, q[:7])
    for r in S.get(ap, ()):
        if r[0] <= T and r[1] > 0 and (melhor is None or r[1] < melhor[0]):
            melhor = (r[1], "Steam", r[0].strftime("%Y-%m"))
    return melhor


def limites(mn):
    """Preco que conta como novo menor (abaixo de 1% e R$ 0,10 do menor) e como empate (ate 1% / R$ 0,10 acima)."""
    return mn * 0.99 - 10, mn * 1.01 + 10


def corte_para(cheio, lim, estrito):
    """Menor corte inteiro cujo preco fica abaixo (estrito) ou ate o limite; None se nem 95% chega."""
    for c in range(1, 96):
        p = preco_steam(cheio, c)
        if p < lim if estrito else p <= lim:
            return c
    return None


def amostra(S, H):
    R = []
    for y in ANOS_TESTE:
        T = dt(y, 11, 2)
        a, b = inverno(y)
        for ap, rows in S.items():
            if rows[0][0] > T - timedelta(days=60):
                continue
            js = [r for r in janela(rows, a, b) if r[1] > 0]
            if not js:
                continue
            pred, rep, meses, mudou = prever(rows, T)
            cheio = estado(rows, T, [r[0] for r in rows])[2]
            R.append(dict(y=y, ap=ap, alvo=corte_max(rows, a, b), pw=min(r[1] for r in js), pred=pred, cheio=cheio,
                          conf=confianca(pred, rep, meses, mudou), mn=menor_ate(ap, T, S, H), mud=mudou,
                          pr1=not any(corte(r) > 0 for r in rows if r[0] <= T)))
    return R


def distribuicoes(R, min_n=40):
    """Diferencas (corte do inverno - corte previsto) por (confianca, faixa do corte); faixa fina demais cai na confianca."""
    g, gc = collections.defaultdict(list), collections.defaultdict(list)
    for x in R:
        d = x["alvo"] - x["pred"]
        g[(x["conf"], banda(x["pred"]))].append(d)
        gc[x["conf"]].append(d)

    def escolher(conf, pred):
        ds = g.get((conf, banda(pred)), [])
        return ds if len(ds) >= min_n else gc[conf]
    return escolher


def chance(ds, extra):
    """P(corte do inverno >= corte previsto + extra)."""
    return sum(1 for d in ds if d >= extra - 1e-9) / len(ds)


def escada(pred, cheio, mn, ds):
    """Cenarios do jogo: (corte, preco, chance de chegar ao menos nesse corte, 0 acima do menor | 1 empata | 2 novo menor)
    e as chances de empatar/bater o menor historico."""
    lim_novo, lim_emp = limites(mn) if mn else (None, None)
    c_novo = corte_para(cheio, lim_novo, True) if mn else None
    c_emp = corte_para(cheio, lim_emp, False) if mn else None
    p_novo = (chance(ds, c_novo - pred) if c_novo else 0.0) if mn else None
    p_emp = (chance(ds, c_emp - pred) if c_emp else 0.0) if mn else None
    grade = sorted(set(DEGRAUS + [pred]) - {0})
    if pred:
        i = grade.index(pred)
        cortes = {pred}
        if i > 0:
            cortes.add(grade[i - 1])
        cortes.update(grade[i + 1:i + 3])
    else:
        cortes = {0}
        ok = [t for t in DEGRAUS if chance(ds, t) >= 0.03]
        if ok:
            cortes.update({ok[0], ok[len(ok) // 2], ok[-1]})
    for c in (c_novo, c_emp):
        if c:
            cortes.add(next((t for t in grade if t >= c), c))
    linhas = []
    for c in sorted(cortes):
        pr = preco_steam(cheio, c)
        tag = 0 if not mn else 2 if pr < lim_novo else 1 if pr <= lim_emp else 0
        linhas.append([c, pr, round(chance(ds, c - pred) * 100), tag])
    return linhas, p_novo, p_emp


def calibracao(R):
    """Deixa um ano de fora: chance prevista x o que aconteceu, por ano e por faixa de chance, para
    "bate o menor" (preco abaixo do recorde) e "chega no menor" (empata ou bate)."""
    anos, caixas = {}, {"novo": collections.defaultdict(lambda: [0, 0.0, 0]), "emp": collections.defaultdict(lambda: [0, 0.0, 0])}
    for y in ANOS_TESTE:
        escolher = distribuicoes([x for x in R if x["y"] != y])
        esp = real = esp_e = real_e = n = 0
        for x in R:
            if x["y"] != y or not x["mn"] or x["pr1"]:   # 1a promocao nao e "bater um recorde": fica de fora, como na pagina
                continue
            ds = escolher(x["conf"], x["pred"])
            lim_novo, lim_emp = limites(x["mn"][0])
            c = corte_para(x["cheio"], lim_novo, True)
            ce = corte_para(x["cheio"], lim_emp, False)
            p = chance(ds, c - x["pred"]) if c else 0.0
            pe = chance(ds, ce - x["pred"]) if ce else 0.0
            ev, ev_e = x["pw"] < lim_novo, x["pw"] <= lim_emp
            esp, real, esp_e, real_e, n = esp + p, real + ev, esp_e + pe, real_e + ev_e, n + 1
            for k, (pp, e) in (("novo", (p, ev)), ("emp", (pe, ev_e))):
                f = 0 if pp < .05 else 1 if pp < .15 else 2 if pp < .30 else 3 if pp < .60 else 4
                caixas[k][f][0] += 1
                caixas[k][f][1] += pp
                caixas[k][f][2] += e
        anos[y] = dict(n=n, esp=round(esp), real=real, esp_e=round(esp_e), real_e=real_e)
    nomes = ["menos de 5%", "5% a 15%", "15% a 30%", "30% a 60%", "60% ou mais"]
    saida = {k: [dict(faixa=nomes[f], n=v[0], prev=v[1] / v[0], real=v[2] / v[0]) for f, v in sorted(c.items())] for k, c in caixas.items()}
    return anos, saida


def inverno_do_jogo(rows, ap, S, H):
    """[ano, melhor corte antes (previsao de nov), corte no inverno, menor preco no inverno, 1 se foi menor historico]."""
    out = []
    for y in range(2022, ANO):
        T = dt(y, 11, 2)
        a, b = inverno(y)
        if rows[0][0] > T - timedelta(days=60):
            continue
        js = [r for r in janela(rows, a, b) if r[1] > 0]
        if not js:
            continue
        pw = min(r[1] for r in js)
        mn = menor_ate(ap, T, S, H)
        out.append([y, prever(rows, T)[0], corte_max(rows, a, b), pw, int(bool(mn) and pw < limites(mn[0])[0]) if y >= 2023 else -1])
    return out


def main():
    cfg = json.load(open(os.path.join(DADOS, "config.json"), encoding="utf-8"))
    lojas = [l for l in cfg.get("lojas", []) if not (cfg.get("somente_drm_steam") and l in LOJAS_SEM_STEAM)] or ["Steam"]
    con = sqlite3.connect("file:" + BANCO.replace("\\", "/") + "?mode=ro", uri=True)
    jogos, S = carregar(con)
    H = historico_lojas(con, jogos, lojas)
    R = amostra(S, H)
    escolher = distribuicoes(R)
    cal_anos, cal_caixas = calibracao(R)
    manual = {r[0]: r[1] for r in con.execute("SELECT appid,nome FROM franquia_manual")}
    fr = series.franquias([{"appid": a, "nome": j["nome"], "franquia": j["franquia"]} for a, j in jogos.items()], manual)
    linhas, sem = [], collections.Counter()
    for ap, j in jogos.items():
        rows = S.get(ap)
        if j["gratis"] or j["breve"] or not j["ch"]:
            sem["grátis ou ainda sem lançamento" if (j["gratis"] or j["breve"]) else "sem preço na Steam"] += 1
            continue
        if not rows:
            sem["sem histórico de preço"] += 1
            continue
        pred, rep, meses, mudou = prever(rows, AGORA, j["ch"])
        conf = confianca(pred, rep, meses, mudou)
        ds = escolher(conf, pred)
        mn = menor_ate(ap, AGORA, S, H)
        if j["p"] and j["p"] > 0 and (not mn or j["p"] < mn[0]):     # o preco de hoje tambem conta (o historico pode atrasar)
            mn = (j["p"], "Steam", AGORA.strftime("%Y-%m"))
        pr1 = not any(corte(r) > 0 for r in rows)                     # nunca teve promocao: o "recorde" e o preco cheio
        esc, p_novo, p_emp = escada(pred, j["ch"], None if pr1 else (mn[0] if mn else None), ds)
        p1 = round(chance(ds, 1 - pred) * 100) if pr1 else None
        linhas.append(dict(a=ap, n=j["nome"], t=j["tipo"], f=fr[ap], pri=j["pri"], h=j["p"], ch=j["ch"], hc=j["co"],
                           pc=pred, pp=preco_steam(j["ch"], pred), c=conf, mud=int(mudou), rep=rep, m=round(meses),
                           mn=mn[0] if mn else None, ml=mn[1] if mn else "", mq=mn[2] if mn else "", e=esc,
                           pn=None if p_novo is None else round(p_novo * 100), pe=None if p_emp is None else round(p_emp * 100), p1=p1,
                           hoje_no_menor=int(bool(mn) and (j["p"] or 0) <= mn[0] * 1.01 + 10 and not pr1),
                           iv=inverno_do_jogo(rows, ap, S, H), ano=datetime.fromtimestamp(j["lanc"], UTC).year if j["lanc"] else 0,
                           rc=j["rc"], cv=capa_curta(j["cv"]), hd=capa_curta(j["hd"])))
    taxa_novo = {}
    for y in ANOS_TESTE:
        v = [x for x in R if x["y"] == y and x["mn"] and not x["pr1"]]
        taxa_novo[y] = round(100 * sum(x["pw"] < limites(x["mn"][0])[0] for x in v) / len(v), 1)
    meta = dict(gerado=AGORA.strftime("%d/%m/%Y"), inicio=INICIO_SALE, fim=FIM_SALE, lojas=len(lojas), sem=dict(sem),
                total=len(jogos), cal_anos=cal_anos, cal_caixas=cal_caixas, taxa_novo=taxa_novo)
    modelo = open(os.path.join(RAIZ, "tools", "prever_winter_sale.html"), encoding="utf-8").read()
    html = modelo.replace("/*DADOS*/", "const L=%s, M=%s;" % (json.dumps(linhas, ensure_ascii=False, separators=(",", ":")),
                                                            json.dumps(meta, ensure_ascii=False, separators=(",", ":"))))
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    open(SAIDA, "w", encoding="utf-8").write(html)
    print("ok:", SAIDA, "%d jogos com previsão, %d sem, %d KB" % (len(linhas), sum(sem.values()), len(html) // 1024))
    print("novo menor por inverno (real):", taxa_novo, "| calibração:", {y: (v["esp"], v["real"]) for y, v in cal_anos.items()})
    print("esperado em 2026: novo menor %.0f, chega no menor %.0f" % (sum((l["pn"] or 0) for l in linhas) / 100,
                                                                      sum((l["pe"] or 0) for l in linhas) / 100))
    print(collections.Counter(l["c"] for l in linhas), len(set(l["f"] for l in linhas)), "franquias")


if __name__ == "__main__":
    main()
