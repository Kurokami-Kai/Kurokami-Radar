"""O que comprar agora e o que esperar na Winter Sale da Steam, para a lista de desejos (so leitura do banco).

Reaproveita a previsao de prever_winter_sale.py (escada de cenarios por jogo, recorde no regime do preco cheio) e junta:
- a pergunta que importa para quem compra: o preco do inverno fica abaixo do de hoje? quanto e com que chance? chega no
  piso da Steam (menor preco da Steam desde que vale o preco cheio de hoje)?
- a trajetoria de desconto por idade: em quantos meses depois do lancamento os jogos chegam a -33/-50/-66/-75%
  (Kaplan-Meier com ~6 mil lancamentos desde out/2021, por faixa de preco cheio), para saber se um jogo novo ainda
  esta longe do apice tipico e vale esperar alem do inverno.
O veredito de cada jogo e testado nos invernos 2023-2025 so com o que se sabia em 2 de novembro (ano de fora).
Gera dados/recomendacoes-winter-sale-2026.html (pagina principal) e refaz dados/previsao-winter-sale-2026.html.

Uso: py tools/recomendar_winter_sale.py [banco.sqlite3] [saida.html]
"""
import bisect
import collections
import json
import os
import sys
from datetime import datetime

import prever_winter_sale as pw

SAIDA = os.path.join(pw.RAIZ, "dados", "recomendacoes-winter-sale-%d.html" % pw.ANO)
K = (33, 50, 66, 75)                    # degraus do apice ("primario" = o maior que a faixa costuma alcancar em 3 anos)
INICIO_HIST = pw.dt(2021, 10, 20)       # a ITAD comeca em out/2021: so lancamentos depois disso tem a trajetoria inteira
MESES_TIRA = 36                         # tira de calor: ultimos 36 meses
DIA = 86400
MIN_RISCO = 30                          # curva por idade so vai ate onde ha 30+ jogos sem ter chegado ao degrau


def faixa(tipo, cheio):
    """Faixa de preco cheio (centavos) para a trajetoria: DLC numa faixa so; jogo em 4."""
    if tipo == "dlc":
        return "dlc"
    return "aaa" if cheio >= 19900 else "alto" if cheio >= 9900 else "medio" if cheio >= 3990 else "barato"


NOME_FAIXA = {"aaa": "jogos de R$ 199 ou mais", "alto": "jogos de R$ 99 a R$ 198", "medio": "jogos de R$ 39,90 a R$ 98",
              "barato": "jogos abaixo de R$ 39,90", "dlc": "DLCs"}


# ---------------------------------------------------------------- trajetoria por idade
def lancamentos(con):
    """[(faixa, lancamento epoch, {k: segundos ate o 1o corte >= k})] de todo o banco: Steam inteira (promo_hist) + lista."""
    L = {}
    for a, l, tp in con.execute("SELECT appid,lancamento,tipo FROM steam_promo WHERE lancamento>0"):
        L[a] = (l, tp)
    for a, l, tp in con.execute("SELECT appid,lancamento,tipo FROM jogo WHERE lancamento>0"):
        L[a] = (l, tp)
    S = collections.defaultdict(list)
    for a, q, pr, ch, co in con.execute("SELECT appid,quando,preco,cheio,corte FROM promo_hist WHERE loja='Steam' UNION "
                                        "SELECT appid,quando,preco,cheio,corte FROM preco WHERE loja='Steam'"):
        if a in L and L[a][0] > INICIO_HIST.timestamp():
            S[a].append((q, pr, ch, co))
    D = []
    for a, rows in S.items():
        l, tp = L[a]
        if tp not in ("jogo", "dlc"):
            continue
        rows.sort()
        if datetime.fromisoformat(rows[0][0]).timestamp() - l > 45 * DIA:   # historico comeca longe do lancamento
            continue
        ch0 = next((r[2] for r in rows if r[2] > 0), 0)
        if not ch0:
            continue
        ev = {}
        for q, pr, ch, co in rows:
            if pr > 0 and 0 < co < 100:
                d = max(datetime.fromisoformat(q).timestamp() - l, 0)
                for k in K:
                    if co >= k and k not in ev:
                        ev[k] = d
        D.append((faixa(tp, ch0), l, ev))
    return D


class Curva:
    """Kaplan-Meier: P(o jogo ja chegou a -k% com t segundos de vida), so com o que se via em T. A curva para onde
    restam menos de MIN_RISCO jogos sem chegar (a cauda com 2 ou 3 jogos ia a 0 e dava "98% de chance")."""

    def __init__(self, itens):
        ev = sorted(itens)
        n, s, self.t, self.s = len(ev), 1.0, [0.0], [1.0]
        i, self.fim = 0, 0.0
        while i < len(ev) and n >= MIN_RISCO:
            t, d, c = ev[i][0], 0, 0
            self.fim = t
            while i < len(ev) and ev[i][0] == t:
                d, c, i = d + ev[i][1], c + 1, i + 1
            if d and n:
                s *= 1 - d / n
                self.t.append(t)
                self.s.append(s)
            n -= c
        self.n = len(ev)

    def sobra(self, t):
        return self.s[bisect.bisect_right(self.t, t) - 1]

    def chega(self, t1, t2):
        """P(chegar ate a idade t2 | nao chegou ate t1); None se t1 ja passa do que a curva ve (t2 alem dela conta so ate o fim)."""
        if t1 >= self.fim:
            return None
        s1 = self.sobra(t1)
        return 1 - self.sobra(min(t2, self.fim)) / s1 if s1 > 1e-9 else 1.0

    def mediana(self):
        """Idade (meses) em que metade ja chegou; None se nao chega a metade no que se ve."""
        i = next((i for i, s in enumerate(self.s) if s <= 0.5), None)
        return round(self.t[i] / DIA / 30.4) if i is not None else None


def curvas(D, T):
    """{(faixa, k): Curva} com os lancamentos ate T-30 dias, eventos vistos so ate T."""
    tT = T.timestamp()
    out = {}
    for fx in NOME_FAIXA:
        base = [(l, ev) for f, l, ev in D if f == fx and l < tT - 30 * DIA]
        for k in K:
            itens = []
            for l, ev in base:
                obs = tT - l
                e = ev.get(k)
                itens.append((e, 1) if e is not None and e <= obs else (obs, 0))
            out[(fx, k)] = Curva(itens)
    return out


def apice(C, fx):
    """Maior degrau que metade da faixa alcanca em 3 anos de vida (o "apice primario" tipico)."""
    ok = [k for k in K if C[(fx, k)].sobra(3 * 365 * DIA) <= 0.5]
    return ok[-1] if ok else K[0]


# ---------------------------------------------------------------- veredito
def precos_inverno(pred, cheio, ds):
    """Precos possiveis no inverno, um por caso da distribuicao (corte previsto + diferenca vista nos invernos)."""
    return sorted(pw.preco_steam(cheio, min(max(pred + d, 0), 95)) for d in ds)


def quantil(v, q):
    return v[min(int(q * len(v)), len(v) - 1)]


def veredito(hoje, hc, cheio, pred, ds, piso_st, idade, mx, C, fx):
    """Numeros e veredito de um jogo; tudo so com o que se sabia no momento (hoje = preco da Steam agora).
    Vereditos: compre (oferta de hoje dificilmente sera batida), alem (jogo novo longe do apice: o inverno provavelmente
    fica 15+ pontos abaixo do apice tipico da faixa e a curva diz que ele chega la ate o proximo inverno),
    espere (o inverno deve ficar mais barato que hoje), sem (sem promocao prevista), talvez (diferenca pequena)."""
    W = precos_inverno(pred, cheio, ds)
    n = len(W)
    margem = max(hoje * 0.01, 10)
    p_cai = sum(1 for w in W if w < hoje - margem) / n
    p_promo = sum(1 for w in W if w < cheio) / n
    ew = sum(W) / n
    lim_novo, lim_emp = pw.limites(piso_st) if piso_st else (None, None)
    p_piso = sum(1 for w in W if w <= lim_emp) / n if piso_st else None
    p_novo = sum(1 for w in W if w < lim_novo) / n if piso_st else None
    o = dict(W=W, p_cai=p_cai, p_promo=p_promo, ew=ew, eco=hoje - ew, mediana=quantil(W, .5), bom=quantil(W, .15),
             p_piso=p_piso, p_novo=p_novo)
    # apice: so jogos com trajetoria conhecida (lancados ha menos de 4 anos)
    ap = None
    if idade is not None and idade < 4 * 365 * DIA and C:
        k = apice(C, fx)
        if mx < k:
            t_inv = idade + 50 * DIA                     # fim da Winter Sale
            p_inv = sum(1 for w in W if w <= pw.preco_steam(cheio, k)) / n
            p_ano = C[(fx, k)].chega(idade, idade + 410 * DIA)   # ate o fim do proximo inverno (None: a curva nao ve tao longe)
            if p_ano is not None:
                ap = dict(k=k, p_inv=p_inv, p_ano=p_ano, med=C[(fx, k)].mediana(), t_inv=t_inv)
    o["ap"] = ap
    o["cm"] = round(100 * (1 - o["mediana"] / cheio))            # corte do preco provavel do inverno
    if ap and ap["p_inv"] < .5 and ap["p_ano"] >= .5 and ap["k"] - o["cm"] >= 15:
        o["v"] = "alem"
    elif hc and (p_cai < .4 or (piso_st and hoje <= lim_emp and (p_novo or 0) < .3)):
        o["v"] = "compre"
    elif p_cai >= .5 and o["eco"] >= max(200, hoje * .05):
        o["v"] = "espere"
    elif p_promo < .4 and not hc:
        o["v"] = "sem"
    else:
        o["v"] = "talvez"
    return o


def max_corte(rows, desde, T):
    return max((pw.corte(r) for r in rows if (desde is None or r[0] >= desde) and r[0] <= T), default=0)


def idade_em(lanc, T):
    return T.timestamp() - lanc if lanc else None


# ---------------------------------------------------------------- backtest
def backtest(ctx, D):
    """Veredito de cada jogo em 2 de novembro de 2023/2024/2025 (distribuicoes sem o ano testado, curvas so com o que
    se via na data) x o que aconteceu: o inverno ficou mais barato que o preco de 2/11? o ano seguinte (em 2025, so ate
    hoje) ficou 10% abaixo do inverno? o jogo novo chegou ao apice da faixa?"""
    R, S, jogos = ctx["R"], ctx["S"], ctx["jogos"]
    res = collections.defaultdict(lambda: dict(n=0, cai=0, eco=0.0, depois_n=0, depois_menor=0, ap_n=0, apice=0, piso=0, sem=0))
    caixas = collections.defaultdict(lambda: [0, 0.0, 0])
    for y in pw.ANOS_TESTE:
        T = pw.dt(y, 11, 2)
        escolher = pw.distribuicoes([x for x in R if x["y"] != y])
        C = curvas(D, T)
        for x in R:
            if x["y"] != y or not x["hoje"]:
                continue
            j, rows = jogos[x["ap"]], S[x["ap"]]
            ts = [r[0] for r in rows]
            e = pw.estado(rows, T, ts)
            ini = pw.regime_inicio(rows, x["cheio"], T)
            fx = faixa(j["tipo"], x["cheio"])
            o = veredito(x["hoje"], pw.corte(e), x["cheio"], x["pred"], escolher(x["conf"], x["pred"]),
                         None if x["pr1"] else (x["ms"][0] if x["ms"] else None), idade_em(j["lanc"], T),
                         max_corte(rows, ini, T), C, fx)
            r = res[o["v"]]
            r["n"] += 1
            cai = x["pw"] < x["hoje"] - max(x["hoje"] * .01, 10)
            r["cai"] += cai
            r["eco"] += (x["hoje"] - x["pw"]) / x["hoje"]
            r["sem"] += x["alvo"] == 0
            if o["p_piso"] is not None:
                r["piso"] += x["pw"] <= pw.limites(x["ms"][0])[1]
            f = min(int(o["p_cai"] * 5), 4)
            caixas[f][0] += 1
            caixas[f][1] += o["p_cai"]
            caixas[f][2] += cai
            if x["depois"] is not None:
                r["depois_n"] += 1
                r["depois_menor"] += x["depois"] < x["pw"] * .9
                if o["ap"]:
                    k = o["ap"]["k"]
                    r["ap_n"] += 1
                    r["apice"] += x["depois"] <= pw.preco_steam(x["cheio"], k) * 1.01 + 10 or x["pw"] <= pw.preco_steam(x["cheio"], k) * 1.01 + 10
    nomes = ["menos de 20%", "20% a 40%", "40% a 60%", "60% a 80%", "80% ou mais"]
    cx = [dict(faixa=nomes[f], n=v[0], prev=round(100 * v[1] / v[0]), real=round(100 * v[2] / v[0])) for f, v in sorted(caixas.items())]
    tab = {k: dict(n=v["n"], cai=round(100 * v["cai"] / v["n"]), eco=round(100 * v["eco"] / v["n"]), sem=round(100 * v["sem"] / v["n"]),
                   depois_n=v["depois_n"], depois=round(100 * v["depois_menor"] / v["depois_n"]) if v["depois_n"] else None,
                   ap_n=v["ap_n"], apice=round(100 * v["apice"] / v["ap_n"]) if v["ap_n"] else None) for k, v in res.items()}
    return tab, cx


def calibrar_idade(D):
    """A curva por idade testada em todos os lancamentos do banco: em 2/11/2023 e 2/11/2024, para cada jogo com menos de
    4 anos que ainda nao tinha chegado ao apice da faixa, a chance prevista de chegar ate o fim do inverno seguinte ao
    proximo (410 dias) x o que aconteceu."""
    cx = collections.defaultdict(lambda: [0, 0.0, 0])
    for y in (2023, 2024):
        T = pw.dt(y, 11, 2)
        C, tT = curvas(D, T), T.timestamp()
        for fx, l, ev in D:
            idade = tT - l
            if idade < 30 * DIA or idade > 4 * 365 * DIA:
                continue
            k = apice(C, fx)
            if ev.get(k) is not None and ev[k] <= idade:
                continue
            if idade + 410 * DIA > C[(fx, k)].fim:           # so onde a curva da data ja via a idade inteira
                continue
            p = C[(fx, k)].chega(idade, idade + 410 * DIA)
            f = min(int(p * 5), 4)
            cx[f][0] += 1
            cx[f][1] += p
            cx[f][2] += ev.get(k) is not None and ev[k] <= idade + 410 * DIA
    nomes = ["menos de 20%", "20% a 40%", "40% a 60%", "60% a 80%", "80% ou mais"]
    return [dict(faixa=nomes[f], n=v[0], prev=round(100 * v[1] / v[0]), real=round(100 * v[2] / v[0])) for f, v in sorted(cx.items())]


# ---------------------------------------------------------------- pagina
def mesas():
    """[(inicio, fim)] dos ultimos 36 meses; o ultimo e o mes de hoje ate agora."""
    n = pw.AGORA.year * 12 + pw.AGORA.month - 1
    ini = [pw.dt(m // 12, m % 12 + 1, 1) for m in range(n - MESES_TIRA + 1, n + 2)]
    return [(ini[i], min(ini[i + 1], pw.AGORA)) for i in range(MESES_TIRA)]


def tira(rows, ini):
    """Maior corte da Steam em cada um dos ultimos 36 meses, um caractere por mes (corte//5 em base 20; '.' sem historico),
    e o indice do mes em que comecou o preco cheio de hoje (-1 se antes)."""
    meses = mesas()
    s = ""
    for a, b in meses:
        if rows[0][0] > b:
            s += "."
            continue
        c = pw.corte_max(rows, a, b) or 0
        s += "0123456789abcdefghij"[min(c // 5, 19)]
    ri = -1
    if ini:
        ri = next((i for i, (a, b) in enumerate(meses) if ini < b), len(meses) - 1)
        if ini < meses[0][0]:
            ri = -1
    return s, ri, meses[0][0].strftime("%Y-%m")


def curta(u, a, padrao):
    """Capa sem 'appid/' nem '?t=' (a pagina recoloca); 1 = o nome padrao da Steam."""
    if not u or u.startswith("http"):
        return u
    u = u.split("?")[0]
    u = u[len(str(a)) + 1:] if u.startswith("%d/" % a) else "/" + u
    return 1 if u == padrao else u


def oportunidade(o, hoje, j, tipo):
    """Nota de "melhor oportunidade": fracao economizada x raiz da economia em reais (ate R$ 200, para um -90% de R$ 3
    nao vencer um -60% de R$ 300) x chance de chegar no menor da Steam x avaliacao; DLC vale menos."""
    e = max(o["eco"], 0)
    return round(1000 * e / hoje * (min(e, 20000) / 20000) ** .5 * (0.5 + 0.5 * (o["p_piso"] or 0)) * nota(j["rp"], j["rc"])
                 * (0.6 if tipo == "dlc" else 1))


def nota(rp, rc):
    return 1.0 if (rp or 0) >= 85 and (rc or 0) >= 500 else .85 if (rp or 0) >= 75 else .6


def main():
    banco = sys.argv[1] if len(sys.argv) > 1 else pw.BANCO
    saida = sys.argv[2] if len(sys.argv) > 2 else SAIDA
    linhas, meta, ctx = pw.analisar(banco)
    pw.escrever(linhas, meta)
    D = lancamentos(ctx["con"])
    C = curvas(D, pw.AGORA)
    bt, bt_cx = backtest(ctx, D)
    bt_ap = calibrar_idade(D)
    jogos, X = ctx["jogos"], ctx["X"]
    saida_l, cont = [], collections.Counter()
    for l in linhas:
        j, x = jogos[l["a"]], X[l["a"]]
        hoje = l["h"] or l["ch"]
        fx = faixa(l["t"], next((r[2] for r in x["rows"] if r[2] > 0), l["ch"]) if j["lanc"] and j["lanc"] > INICIO_HIST.timestamp() else l["ch"])
        piso = None if l["p1"] is not None else l["ms"]
        o = veredito(hoje, l["hc"], l["ch"], l["pc"], x["ds"], piso, idade_em(j["lanc"], pw.AGORA),
                     max(max_corte(x["rows"], x["ini"], pw.AGORA), l["hc"] or 0), C, fx)
        cont[o["v"]] += 1
        t, ri, t0 = tira(x["rows"], x["ini"])
        ap = o["ap"]
        fim = j.get("fim")
        saida_l.append(dict(
            a=l["a"], n=l["n"], t=l["t"], f=l["f"], v=o["v"], h=hoje, ch=l["ch"], hc=l["hc"], fim=datetime.fromtimestamp(fim, pw.UTC).strftime("%d/%m") if fim and l["hc"] else None,
            pc=l["pc"], md=o["mediana"], bm=o["bom"], ew=round(o["ew"]), pcai=round(o["p_cai"] * 100), pp=round(o["p_promo"] * 100),
            pz=None if o["p_piso"] is None else round(o["p_piso"] * 100), pn=None if o["p_novo"] is None else round(o["p_novo"] * 100),
            p1=l["p1"], ms=l["ms"], msq=l["msq"], mn=l["mn"], ml=l["ml"], mq=l["mq"], mb=l["mb"], mbl=l["mbl"], mbq=l["mbq"],
            ri=l["ri"], rc0=l["rc0"], e=[r[:3] for r in l["e"]], c=l["c"], m=l["m"], ano=l["ano"],
            id=None if not j["lanc"] else round((pw.AGORA.timestamp() - j["lanc"]) / DIA / 30.4),
            mx=max(max_corte(x["rows"], x["ini"], pw.AGORA), l["hc"] or 0), fx=fx,
            ak=ap["k"] if ap else None, ai=round(ap["p_inv"] * 100) if ap else None, aa=round(ap["p_ano"] * 100) if ap else None,
            am=ap["med"] if ap else None, cm=o["cm"], rp=j["rp"], rc=j["rc"], pri=l["pri"] or None, tr=t, tri=ri,
            sc=oportunidade(o, hoje, j, l["t"]),
            cv=curta(l["cv"], l["a"], "library_600x900_2x.jpg"), hd=curta(l["hd"], l["a"], "header.jpg")))
        saida_l[-1] = {k: v for k, v in saida_l[-1].items() if v is not None and v != ""}
    traj = {fx: dict(nome=NOME_FAIXA[fx], n=C[(fx, 50)].n, apice=apice(C, fx),
                     k={k: dict(med=C[(fx, k)].mediana(), **{"m%d" % m: round(100 * (1 - C[(fx, k)].sobra(m * 30.4 * DIA))) for m in (6, 12, 24, 36)})
                        for k in K}) for fx in NOME_FAIXA}
    meta.update(bt=bt, bt_cx=bt_cx, bt_ap=bt_ap, traj=traj, cont=dict(cont), tira_ini=mesas()[0][0].strftime("%Y-%m"), hoje_mes=pw.AGORA.strftime("%Y-%m"))
    modelo = open(os.path.join(pw.RAIZ, "tools", "recomendar_winter_sale.html"), encoding="utf-8").read()
    html = modelo.replace("/*DADOS*/", "const L=%s, M=%s;" % (json.dumps(saida_l, ensure_ascii=False, separators=(",", ":")),
                                                            json.dumps(meta, ensure_ascii=False, separators=(",", ":"))))
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    open(saida, "w", encoding="utf-8").write(html)
    print("ok:", saida, "%d KB" % (len(html) // 1024))
    print("vereditos:", dict(cont))
    print("backtest:", json.dumps(bt, ensure_ascii=False))
    print("p_cai calibração:", bt_cx)
    print("ápice calibração:", bt_ap)
    print("trajetória:", {fx: (v["n"], v["apice"], {k: v["k"][k]["med"] for k in K}) for fx, v in traj.items()})


if __name__ == "__main__":
    main()
