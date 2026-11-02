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
import sys
import unicodedata
from datetime import datetime, timedelta

import prever_winter_sale as pw
import recomendar_winter_sale as rw

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
        out.append({kk: vv for kk, vv in dict(
            a=a, n=j["nome"], v=v, ch=ch, h=h, hc=hc or None, of=of[0], ol=of[1], k=k, ag=agora, on=onde,
            w=win, wb=bom if bom < win else None, wl=wl, eco=max(agora - win, 0), pc=round(o["p_cai"] * 100),
            m=m[:2], pri=l["pri"] or None, rp=j["rp"], hd=rw.curta(l["hd"], a, "header.jpg"),
            cv=rw.curta(l["cv"], a, "library_600x900_2x.jpg")).items() if vv is not None and vv != ""})
    teste = teste_2025(ctx, HL)
    meta = dict(gerado=meta["gerado"], inicio=meta["inicio"], fim=meta["fim"], cont=dict(cont), fora=dict(fora),
                sem=meta["sem"], teste=teste, n=len(out))
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
