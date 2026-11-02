"""Winter Sale na lista de desejos, simples: para cada JOGO da lista (sem DLC, sem o que voce ja tem), o preco de hoje
(melhor loja oficial e keyshop), o preco provavel no inverno em qualquer loja e um motivo curto (so leitura do banco).

Preco do inverno = corte provavel da Steam (previsao de prever_winter_sale.py) x quanto a melhor loja oficial ficou abaixo
da Steam nos invernos passados do mesmo preco cheio (Nuuvem, GMG, Fanatical... costumam ir alem da Steam). Keyshop
(GG.deals) so tem historico desde out/2026: entra com o preco de hoje. Cupom de loja nao aparece no historico.
Testado no inverno 2025 com o que se sabia em 2 de novembro.

Jogos que voce tem fora da Steam: um nome por linha em dados/ja-tenho.txt (pasta fora do Git).
Uso: py tools/winter_sale_desejos.py [banco.sqlite3] [saida.html]
"""
import bisect
import collections
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timedelta

import prever_winter_sale as pw
import recomendar_winter_sale as rw
from radar import analise  # noqa: E402 (prever_winter_sale ja pos a raiz no sys.path)

SAIDA = os.path.join(pw.RAIZ, "dados", "winter-sale-lista-de-desejos.html")
JA_TENHO = os.path.join(pw.RAIZ, "dados", "ja-tenho.txt")
KEYSHOP = "GG.deals keyshop"
DIAS_KEY = 10                 # preco de keyshop vale se foi visto nos ultimos 10 dias
VALIDADE = 365                # estado de uma loja so vale se o registro tem ate 1 ano (loja que parou de vender some)


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def lojas_por_jogo(H):
    """appid -> loja -> ([quando datetime], [preco])."""
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: ([], [])))
    for a, regs in H.items():
        for q, pr, loja in regs:
            ts, ps = out[a][loja]
            ts.append(datetime.fromisoformat(q))
            ps.append(pr)
    return out


def menor_lojas(HL, a, ini, fim):
    """(menor preco, loja) nas lojas oficiais entre ini e fim (estado em ini + mudancas ate fim)."""
    melhor = None
    for loja, (ts, ps) in HL.get(a, {}).items():
        i = bisect.bisect_right(ts, ini) - 1
        cand = [ps[i]] if i >= 0 and ini - ts[i] <= timedelta(days=VALIDADE) else []
        j = bisect.bisect_right(ts, fim)
        cand += ps[i + 1:j]
        for p in cand:
            if melhor is None or p < melhor[0]:
                melhor = (p, loja)
    return melhor


def invernos(rows, a, HL, cheio, ate, lanc):
    """[(ano, menor Steam, menor em qualquer loja, loja)] dos invernos antes de `ate`, depois do lancamento (pre-venda
    nao conta) e com o mesmo preco cheio (+-10%)."""
    out = []
    for y in range(2022, ate):
        ini, fim = pw.inverno(y)
        if lanc and ini.timestamp() < lanc:
            continue
        js = [r for r in pw.janela(rows, ini, fim) if r[1] > 0]
        if not js or abs(js[0][2] - cheio) > pw.FAIXA_CHEIO * cheio:
            continue
        st = min(r[1] for r in js)
        ql = menor_lojas(HL, a, ini, fim)
        out.append((y, st, min(st, ql[0]) if ql else st, ql[1] if ql and ql[0] < st else "Steam"))
    return out


def fator(iv):
    """Quanto a melhor loja ficou abaixo da Steam no inverno mais recente (1 = a Steam foi a mais barata)."""
    return iv[-1][2] / iv[-1][1] if iv else 1.0


def teste_2025(ctx, HL):
    """Inverno 2025 previsto com o que se sabia em 2/11/2025: preco provavel em qualquer loja x o menor que houve."""
    R = [x for x in ctx["R"] if x["y"] == 2025]
    escolher = pw.distribuicoes([x for x in ctx["R"] if x["y"] != 2025])
    erros, perto, cai_ok, cai_n = [], 0, 0, 0
    for x in R:
        rows = ctx["S"][x["ap"]]
        iv = invernos(rows, x["ap"], HL, x["cheio"], 2025, ctx["jogos"][x["ap"]]["lanc"])
        W = rw.precos_inverno(x["pred"], x["cheio"], escolher(x["conf"], x["pred"]))
        prev = rw.quantil(W, .5) * fator(iv)
        ini, fim = pw.inverno(2025)
        ql = menor_lojas(HL, x["ap"], ini, fim)
        real = min(x["pw"], ql[0]) if ql else x["pw"]
        if real <= 0:
            continue
        e = (prev - real) / real
        erros.append(abs(e))
        perto += abs(e) <= .15
        T = pw.dt(2025, 11, 2)
        qh = menor_lojas(HL, x["ap"], T, T)
        hoje = min(x["hoje"], qh[0]) if qh else x["hoje"]
        if prev < hoje * .92:                      # o que a pagina chamaria de "espere"
            cai_n += 1
            cai_ok += real < hoje * .97
    erros.sort()
    return dict(n=len(erros), perto=round(100 * perto / len(erros)), mediana=round(100 * erros[len(erros) // 2]),
                espere=cai_n, espere_ok=round(100 * cai_ok / cai_n) if cai_n else None)


def brl(c):
    return "R$ " + ("%.2f" % (c / 100)).replace(".", ",")


TIPOS = ("selo", "novo", "igual", "24m")              # as 4 caixas do Hunter (analise.TIPOS), da mais forte para a mais fraca
NOME_TIPO = {"selo": "Selo Kurokami", "novo": "Novo recorde", "igual": "Igual ao recorde", "24m": "Menor em 2 anos"}
PESO_TIPO = {"selo": 1.0, "novo": .85, "igual": .7, "24m": .55, None: .3}


def folga(x):
    return max(10, x * 0.01)


def meses_desde(aaaamm):
    y, m = int(aaaamm[:4]), int(aaaamm[5:7])
    return (pw.AGORA.year - y) * 12 + pw.AGORA.month - m


def marca(p, rec, rec_q, m24, tem_promo):
    """Caixa do preco p como o Hunter avisa (analise.analisar), contra o menor do regime em qualquer loja oficial:
    selo (abaixo do recorde, que tem 18+ meses, ou pela metade dele; exige promocao anterior), novo, igual, 24m."""
    if not rec:
        return None
    if p < rec - folga(rec):
        meio = rec / 2
        return "selo" if tem_promo and rec_q and (meses_desde(rec_q) >= 18 or p <= meio + folga(meio)) else "novo"
    if abs(p - rec) <= folga(rec):
        return "igual"
    if m24 and p <= m24 + folga(m24):
        return "24m"
    return None


def qualidade(rp, rc):
    """0..1 pelas analises da Steam; poucas analises pesam menos."""
    q = (rp or 70) / 100
    return q * (.8 if (rc or 0) < 300 else 1)


class SoLeitura:
    """O minimo de radar.banco.Banco que analise.Contexto usa (q), sobre o banco aberto so para leitura."""

    def __init__(self, banco):
        self.con = sqlite3.connect("file:" + banco.replace("\\", "/") + "?mode=ro", uri=True)
        self.con.row_factory = sqlite3.Row

    def q(self, sql, *args):
        return self.con.execute(sql, *args).fetchall()


def cortes_dlc(con):
    """appid -> maior corte da Steam no ultimo ano (promo_hist e preco): o que uma DLC costuma ter numa promocao."""
    desde = (pw.AGORA - timedelta(days=400)).isoformat()
    out = {}
    for tab in ("promo_hist", "preco"):
        for a, c in con.execute("SELECT appid,MAX(corte) FROM %s WHERE loja='Steam' AND quando>=? AND corte<100 GROUP BY appid" % tab, (desde,)):
            out[a] = max(out.get(a) or 0, c or 0)
    return out


def completo(cx, a, w, ch, cm, cd):
    """Jogo + expansoes (DLCs de historia e pacotes que voce nao tem): hoje (o jeito mais barato, com edicoes e bundles,
    analise.melhor_combinacao) e no inverno (o jogo pelo preco provavel + cada DLC pelo maior corte dela no ultimo ano,
    sem passar do corte do jogo; sem historico, ate -50%). None se as expansoes somam menos de 15% do jogo."""
    rel = [d for d in cx.relevantes(a) if d not in cx.possuidos]
    cheios = [cx.jogos.get(d, {}).get("cheio_steam") or 0 for d in rel]
    if not rel or sum(cheios) < ch * .15:
        return None
    mc = cx.melhor_combinacao(a)
    if not mc or not mc.get("custo_completo"):
        return None
    inv = w + round(sum(c * (100 - min(cm, cd.get(d) if cd.get(d) else 50)) / 100 for d, c in zip(rel, cheios)))
    return dict(n=len(rel), hoje=mc["custo_completo"], inv=min(inv, mc["custo_completo"]), cheio=ch + sum(cheios),
                como=mc["nome"] if mc.get("partes") else "")


def apresentacao(out):
    """O que a apresentacao mostra (listas de appids, na ordem): so jogos bem avaliados (80%+ e 300+ analises).
    picks = espere com caixa provavel (Selo/recorde/igual/2 anos), pela forca da caixa x corte x avaliacao;
    ja = o preco de hoje ja e o do inverno e esta numa caixa (ou keyshop abaixo do inverno); recordes = maior chance
    de novo recorde; fr = franquias com 2+ jogos para comprar; dlc = jogo + expansoes; nao = jogos novos longe do
    desconto tipico ou sem promocao prevista."""
    bom = [l for l in out if (l.get("rp") or 0) >= 80 and (l.get("rc") or 0) >= 300]
    q = {l["a"]: qualidade(l.get("rp"), l.get("rc")) for l in out}
    corte = lambda l, p: max(0, 1 - p / l["ch"])                                         # noqa: E731
    picks = sorted((l for l in bom if l["v"] == "espere" and l.get("mk")),     # forca da caixa x avaliacao x desconto x economia
                   key=lambda l: -PESO_TIPO[l["mk"]] * q[l["a"]] * (.5 + corte(l, l["w"])) * (min(l["eco"], 15000) / 15000) ** .5)[:15]
    ja = sorted((l for l in bom if l["v"] == "compre" and (l.get("mag") or (l["on"] == "keyshop" and l["ag"] <= l["w"]))),
                key=lambda l: -corte(l, l["ag"]) * q[l["a"]])[:9]
    rec = sorted((l for l in bom if l["v"] in ("espere", "tanto") and l["cn"]["novo"] >= 50),
                 key=lambda l: -l["cn"]["novo"] * q[l["a"]])[:9]
    grupos = collections.defaultdict(list)
    for l in out:
        if l.get("fr") and l["v"] in ("espere", "compre"):
            grupos[l["fr"]].append(l)
    fr = []
    for nome, ls in grupos.items():
        if len(ls) < 2:
            continue
        hoje, inv = sum(l["ag"] for l in ls), sum(min(l["w"], l["ag"]) for l in ls)
        nota = sum(q[l["a"]] for l in ls) / len(ls)
        fr.append(dict(nome=nome, itens=[l["a"] for l in sorted(ls, key=lambda l: -q[l["a"]])], hoje=hoje, inv=inv,
                       ch=sum(l["ch"] for l in ls), s=(hoje - inv) * nota))
    fr.sort(key=lambda g: -g["s"])
    dlc = sorted((l for l in bom if l.get("cp") and l["cp"]["n"] <= 8 and l["v"] != "nao"),
                 key=lambda l: -(l["cp"]["cheio"] - min(l["cp"]["hoje"], l["cp"]["inv"])) * q[l["a"]])[:6]
    nao = sorted((l for l in bom if l.get("al") or l["v"] == "nao"), key=lambda l: -(l.get("rc") or 0))[:8]
    return dict(picks=[l["a"] for l in picks], ja=[l["a"] for l in ja], rec=[l["a"] for l in rec],
                fr=[{k: v for k, v in g.items() if k != "s"} for g in fr[:6]], nfr=len(fr),
                dlc=[l["a"] for l in dlc], nao=[l["a"] for l in nao])


def main():
    banco = sys.argv[1] if len(sys.argv) > 1 else pw.BANCO
    saida = sys.argv[2] if len(sys.argv) > 2 else SAIDA
    linhas, meta, ctx = pw.analisar(banco)
    con, jogos, X = ctx["con"], ctx["jogos"], ctx["X"]
    HL = lojas_por_jogo(ctx["H"])
    D = rw.lancamentos(con)
    C = rw.curvas(D, pw.AGORA)
    tenho = {norm(l) for l in open(JA_TENHO, encoding="utf-8")} - {""} if os.path.exists(JA_TENHO) else set()
    oficial, steam = collections.defaultdict(list), {}
    lojas = set(ctx["lojas"]) | {"Steam"}
    for a, loja, pr, cheio, co in con.execute("SELECT appid,loja,preco,cheio,corte FROM oferta_atual WHERE preco>0"):
        if loja in lojas:
            oficial[a].append((pr, loja))
        if loja == "Steam":
            steam[a] = (pr, cheio or pr, co or 0)
    desde = (pw.AGORA - timedelta(days=DIAS_KEY)).isoformat()
    key = {}
    for a, pr, q in con.execute("SELECT appid,preco,quando FROM preco WHERE loja=? AND quando>=? AND preco>0 ORDER BY quando", (KEYSHOP, desde)):
        key[a] = pr                                 # o mais recente fica
    cfg = json.load(open(os.path.join(pw.DADOS, "config.json"), encoding="utf-8"))
    cx = analise.Contexto(SoLeitura(banco), dict(cfg, dlc=dict(cfg.get("dlc") or {}, so_expansoes=True)))
    cd = cortes_dlc(con)
    fora, out, cont = collections.Counter(), [], collections.Counter()
    for l in linhas:
        a, j = l["a"], jogos[l["a"]]
        if l["t"] != "jogo":
            fora["DLC"] += 1
            continue
        if norm(j["nome"]) in tenho:
            fora["já tenho"] += 1
            continue
        if a not in steam:
            fora["fora da Steam hoje"] += 1
            continue
        x = X[a]
        ch, h, hc = l["ch"], l["h"] or l["ch"], l["hc"]
        if abs(steam[a][1] - ch) > pw.FAIXA_CHEIO * ch:      # preco do jogo errado (pacote): vale o da oferta da Steam
            h, ch, hc = steam[a]
            l["rc0"] = l["p1"] = None
        fx = rw.faixa(l["t"], ch)
        piso = None if l["p1"] is not None else l["ms"]
        o = rw.veredito(h, hc, ch, l["pc"], x["ds"], piso, rw.idade_em(j["lanc"], pw.AGORA),
                        max(rw.max_corte(x["rows"], x["ini"], pw.AGORA), hc or 0), C, fx)
        iv = invernos(x["rows"], a, HL, ch, pw.ANO, j["lanc"])
        f = fator(iv)
        win = round(o["mediana"] * f)
        bom = round(o["bom"] * f)
        wl = iv[-1][3] if iv and f < .99 else "Steam"
        of = min(oficial.get(a) or [(h, "Steam")])
        k = key.get(a)
        agora, onde = (k, "keyshop") if k and k < of[0] else of
        # veredito em 4 cestas, so com numeros que a pessoa ve na tela
        if o["p_promo"] < .4 and not hc and agora >= ch * .97:
            v = "nao"
        elif win < agora - max(300, agora * .08) and o["p_cai"] >= .5:
            v = "espere"
        elif agora <= win + max(200, win * .03):
            v = "compre"
        else:
            v = "tanto"
        cont[v] += 1
        # motivos: no maximo 2, os que explicam o numero do inverno
        m = []
        if iv:
            y, st, qq, lj = iv[-1]
            m.append("Inverno %d: %s na %s (-%d%%)" % (y, brl(qq), lj, round(100 * (1 - qq / ch))))
        elif l["p1"] is not None:
            m.append("Nunca teve promoção neste preço: no inverno seria a 1ª")
        if l["rc0"]:
            m.append("Preço cheio mudou de %s para %s: o histórico antigo não vale" % (brl(l["rc0"]), brl(ch)))
        ap = o["ap"]
        if ap and o["v"] == "alem" and len(m) < 2:
            m.append("Lançado há %d meses: costuma chegar a -%d%% só em ~%d meses" % (
                round(rw.idade_em(j["lanc"], pw.AGORA) / rw.DIA / 30.4), ap["k"], ap["med"] or 24))
        if l["mb"] and len(m) < 2 and not (iv and l["mb"] >= iv[-1][2]):
            m.append("Menor já visto: %s na %s (%s)" % (brl(l["mb"]), l["mbl"], l["mbq"][5:] + "/" + l["mbq"][:4]))
        if not m:
            m.append("Sem histórico de inverno")
        # as 4 caixas: o preco provavel e cada cenario contra o menor do regime (qualquer loja oficial) e o de 24 meses
        rec, rec_l, rec_q = (l["mn"], l["ml"], l["mq"]) if l["mn"] else (None, "", "")
        d24 = max(x["ini"] or pw.dt(2000, 1, 1), pw.AGORA - timedelta(days=730))
        m24 = pw.menor_ate(a, pw.AGORA, ctx["S"], ctx["H"], d24)
        tem_promo = l["p1"] is None
        mk = marca(win, rec, rec_q, m24 and m24[0], tem_promo)
        cen = [marca(w * f, rec, rec_q, m24 and m24[0], tem_promo) for w in o["W"]]
        chance = {t: round(100 * sum(1 for c in cen if c and TIPOS.index(c) <= TIPOS.index(t)) / len(cen)) for t in TIPOS}
        comp = completo(cx, a, win, ch, o["cm"], cd)
        alem = None
        if ap and o["v"] == "alem":
            alem = dict(k=ap["k"], med=ap["med"], idade=round(rw.idade_em(j["lanc"], pw.AGORA) / rw.DIA / 30.4))
        out.append({kk: vv for kk, vv in dict(
            a=a, n=j["nome"], v=v, ch=ch, h=h, hc=hc or None, of=of[0], ol=of[1], k=k, ag=agora, on=onde,
            w=win, wb=bom if bom < win else None, wl=wl, eco=max(agora - win, 0), pc=round(o["p_cai"] * 100),
            mk=mk, cn=chance, rec=rec, recl=rec_l, recq=rec_q, m24=m24 and m24[0], fr=l["f"], cp=comp, al=alem,
            mag=marca(of[0], rec, rec_q, m24 and m24[0], tem_promo) if hc or of[1] != "Steam" else None,
            m=m[:2], pri=l["pri"] or None, rp=j["rp"], rc=j["rc"], hd=rw.curta(l["hd"], a, "header.jpg"),
            cv=rw.curta(l["cv"], a, "library_600x900_2x.jpg")).items() if vv is not None and vv != ""})
    teste = teste_2025(ctx, HL)
    qq = meta["cal_qq"].get(2025) or {}
    meta = dict(gerado=meta["gerado"], inicio=meta["inicio"], fim=meta["fim"], cont=dict(cont), fora=dict(fora),
                sem=meta["sem"], teste=teste, n=len(out), ap=apresentacao(out), rec25=dict(prev=qq.get("esp"), real=qq.get("real")))
    modelo = open(os.path.join(pw.RAIZ, "tools", "winter_sale_desejos.html"), encoding="utf-8").read()
    html = modelo.replace("/*DADOS*/", "const L=%s, M=%s;" % (json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                                                            json.dumps(meta, ensure_ascii=False, separators=(",", ":"))))
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    open(saida, "w", encoding="utf-8").write(html)
    print("ok:", saida, "%d KB" % (len(html) // 1024))
    print("cestas:", dict(cont), "fora:", dict(fora), "sem previsão:", meta["sem"])
    print("teste inverno 2025:", teste)


if __name__ == "__main__":
    main()
