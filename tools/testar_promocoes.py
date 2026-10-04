"""Testa /api/promocoes e /api/vitrine (spec 04, C) numa COPIA do banco real, sem rede.

Uso: py tools/testar_promocoes.py [--banco CAMINHO] [--config CAMINHO]
Imprime os tempos (1a montagem do cache e consultas com o cache pronto; meta <= 300 ms) e confere filtros,
contagens, ordenacao (nulos por ultimo), erros 400 e a vitrine x "Ver tudo". Sai com 1 se algo falhou."""
import argparse
import json
import os
import shutil
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import caminhos  # noqa: E402
from tools.backtest_selo import achar_banco  # noqa: E402

FALHAS = []


def confere(cond, txt):
    print(("  ok   " if cond else "  FALHOU ") + txt)
    if not cond:
        FALHAS.append(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    origem, cfg_arq = (a.banco, a.config) if a.banco else achar_banco()
    tmp = tempfile.mkdtemp(prefix="kr-promo-")
    try:
        shutil.copy2(origem, os.path.join(tmp, "radar.sqlite3"))
        shutil.copy2(a.config or cfg_arq, os.path.join(tmp, "config.json"))
        caminhos.ARQ_BANCO = os.path.join(tmp, "radar.sqlite3")
        caminhos.ARQ_CONFIG = os.path.join(tmp, "config.json")
        caminhos.DADOS = caminhos.SONDA = os.path.join(tmp, "dados")
        carr = os.path.join(os.path.dirname(origem), "carrinho.json")
        caminhos.ARQ_CARRINHO = os.path.join(tmp, "carrinho.json")
        if os.path.isfile(carr):
            shutil.copy2(carr, caminhos.ARQ_CARRINHO)
        testar()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("testar_promocoes: %d falha(s)" % len(FALHAS))
    sys.exit(1 if FALHAS else 0)


def testar():
    from radar import painel

    def q(**kw):
        return painel.api_promocoes({"q": [json.dumps(kw)]})

    print("== tempos")
    t = time.perf_counter(); painel.invalidar_linhas(); q()
    t1 = (time.perf_counter() - t) * 1000
    print("  1a montagem do cache: %.0f ms (montar as linhas: %s ms)" % (t1, painel._LINHAS["ms"]))
    consultas = [{}, {"desconto_min": 50, "analises_de": 5000}, {"mostrar_so": ["novo", "igual"], "ordem": [["volta", "asc"]]},
                 {"busca": "a", "relacao": {"mudo": "excluir"}, "ordem": [["fim", "asc"], ["nome", "desc"]], "por_pagina": 250}]
    tempos = []
    for c in consultas:
        for _ in range(5):
            t = time.perf_counter(); q(**c); tempos.append((time.perf_counter() - t) * 1000)
    print("  com o cache pronto: mediana %.1f ms, máx %.1f ms (%d consultas)" % (statistics.median(tempos), max(tempos), len(tempos)))
    confere(max(tempos) <= 300, "/api/promocoes ≤ 300 ms com o cache pronto")

    itens = painel.linhas_promocoes()[0]
    print("== filtros (%d linhas)" % len(itens))
    tudo = q(por_pagina=250)
    confere(tudo["total"] == len(itens), "sem filtros = todas as linhas")
    for t_ in ("selo", "novo", "igual", "24m"):
        r = q(mostrar_so=[t_])
        confere(r["total"] == tudo["contagens"]["mostrar_so"][t_], "contagem de %s bate com o total ao marcar a caixa (%d)" % (t_, r["total"]))
    r = q(mostrar_so=["novo"], tipo=["jogo"])
    confere(r["total"] == q(mostrar_so=["novo"])["contagens"]["tipo"]["jogo"], "contagem de Tipo usa os outros filtros")
    a = q(relacao={"extra": "exigir", "mudo": "excluir"}, por_pagina=250)
    confere(all(o["extra"] and not o["mudo"] for o in a["itens"]), "✓ Monitorado + ✕ Silenciado combinados (%d)" % a["total"])
    u = q(relacao={"extra": "exigir", "no_carrinho": "exigir"}, qualquer_um=True, por_pagina=250)
    n_uniao = sum(1 for o in itens if o["extra"] or o["no_carrinho"])
    confere(u["total"] == n_uniao, "Qualquer um: ✓ Monitorado + ✓ No carrinho = união (%d)" % n_uniao)
    p = q(desconto_min=50, analises_de=5000, por_pagina=250)
    confere(all(o["corte"] >= 50 and o["rcount"] >= 5000 for o in p["itens"]), "filtros padrão (desconto ≥ 50%%, análises ≥ 5.000): %d" % p["total"])
    sem_lanc = sum(1 for o in itens if not o["lancamento"])
    lz = q(lanc_de="1990-01-01")
    confere(lz["total"] == len(itens) - sem_lanc, "sem data de lançamento fica fora com a faixa ligada")
    pg = q(por_pagina=50, pagina=2)
    confere(pg["itens"] == tudo["itens"][50:100], "página 2 de 50 = itens 51 a 100")

    print("== ordenação")

    def ordem_ok(campo, dir_, chave):
        r = q(ordem=[[campo, dir_]], por_pagina=250)["itens"]
        vals = [chave(o) for o in r]
        cheios = [v for v in vals if v is not None]
        nulos_fim = all(v is None for v in vals[len(cheios):])
        cres = all(x <= y for x, y in zip(cheios, cheios[1:])) if dir_ == "asc" else all(x >= y for x, y in zip(cheios, cheios[1:]))
        return nulos_fim and cres, r
    ok, r = ordem_ok("fim", "asc", lambda o: o["fim"])
    confere(ok, "Termina: o que acaba antes primeiro, sem data no fim")
    ok, r = ordem_ok("inicio", "desc", lambda o: o["inicio"])
    confere(ok, "Começou: o que acabou de entrar primeiro, nulos no fim")
    ok, r = ordem_ok("volta", "asc", lambda o: o["volta_ordem"])
    textos = [o["volta_texto"] for o in r]
    confere(ok and (not textos or textos[0] in ("nunca teve esse desconto", None)),
            "Costuma voltar: \"nunca teve\" primeiro; curto/primeira/vazio no fim")
    fim_ = [x for x in textos if x in ("histórico curto", "primeira promoção", None)]
    confere(textos[len(textos) - len(fim_):] == fim_, "histórico curto, primeira promoção e vazio por último")
    r2 = q(ordem=[["corte", "desc"], ["preco", "asc"]], por_pagina=250)["itens"]
    pares = [(o["corte"], o["preco"]) for o in r2 if o["corte"] and o["preco"] is not None]
    confere(all(a_[0] > b_[0] or (a_[0] == b_[0] and a_[1] <= b_[1]) for a_, b_ in zip(pares, pares[1:])), "dois critérios (corte desc, preço asc)")

    print("== erros 400")
    for ruim, txt in (({"cor": 1}, "campo desconhecido"), ({"mostrar_so": ["raro"]}, "valor desconhecido"),
                      ({"por_pagina": 30}, "por_pagina"), ({"ordem": [["raridade", "desc"]]}, "ordenar por raridade"),
                      ({"relacao": {"favorito": "exigir"}}, "favorito saiu da relação")):
        try:
            q(**ruim); confere(False, "%s → 400" % txt)
        except painel.PedidoInvalido as e:
            confere(True, "%s → 400 (\"%s\")" % (txt, e))

    print("== vitrine × Ver tudo")
    v = painel.api_vitrine({})
    dmin = v["desconto_minimo"]
    vistos = set()
    for t_ in ("selo", "novo", "igual", "24m"):
        filtro = {"mostrar_so": [t_], "relacao": {"tenho": "excluir"}}
        if t_ != "selo":
            filtro["desconto_min"] = dmin
        n = q(**filtro)["total"]
        ids = {o["appid"] for o in v[t_]["itens"]}
        confere(n == v[t_]["total"] and not (ids & vistos), "%s: bloco %d = Ver tudo %d, sem repetir jogo" % (t_, v[t_]["total"], n))
        vistos |= ids
    print("  avisa: %s · na lista: %d" % (v["avisa"], v["na_lista"]))

    print("== ficha (/api/jogo)")
    com_regua = []
    for o in itens:
        if o["corte"] and o["tipo_oferta"] in (None, "novo", "igual", "24m"):
            j = painel.api_jogo({"appid": [str(o["appid"])]})
            if j["regua_steam"]:
                com_regua.append((o["nome"], j["regua_steam"]["texto"]))
    for n, t_ in com_regua[:10]:
        print("  %s: %s" % (n, t_))
    confere(bool(com_regua), "linha da régua da Steam aparece na ficha (%d jogos)" % len(com_regua))
    j = painel.api_jogo({"appid": [str(itens[0]["appid"])]})
    confere(all(k in j for k in ("tipos", "tipo_oferta", "volta_texto", "volta_dica", "regua_steam", "fim")), "/api/jogo tem os campos novos")


if __name__ == "__main__":
    main()
