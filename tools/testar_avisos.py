"""Testa a regra de aviso da 0.15 (spec 04, Aceites 2 a 4) numa COPIA do banco real, sem rede e sem toast de verdade.

Uso: py tools/testar_avisos.py [--banco CAMINHO] [--config CAMINHO]
  2  so o Selo ligado: quantos e quais avisos uma rodada daria hoje (e que nenhum vem de raridade ou favorito)
  3  ligar "Novo recorde" passa a avisar novo com corte >= desconto_minimo; desligar para; 24m abaixo do minimo nao
     avisa; Selo + novo avisa com so "Novo recorde" ligado
  4  ligar um tipo com N jogos ja qualificados = 1 toast de resumo e nenhum aviso individual; quem entra depois avisa
Sai com 1 se algo falhou."""
import argparse
import copy
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import analise, caminhos, config, notificar  # noqa: E402
from tools.backtest_selo import achar_banco  # noqa: E402

FALHAS = []


def confere(cond, txt):
    print(("  ok   " if cond else "  FALHOU ") + txt)
    if not cond:
        FALHAS.append(txt)


def rodada(b, cfg):
    of = {a: [dict(o, drm_steam=True) for o in l] for a, l in b.ofertas_atuais().items()}
    gg = {r["appid"]: dict(r) for r in b.q("SELECT * FROM gg")}
    return analise.avaliar(analise.Contexto(b, cfg), of, gg, set(cfg["lojas"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco"); ap.add_argument("--config")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    origem, cfg_arq = (a.banco, a.config) if a.banco else achar_banco()
    tmp = tempfile.mkdtemp(prefix="kr-avisos-")
    try:
        shutil.copy2(origem, os.path.join(tmp, "radar.sqlite3"))
        shutil.copy2(a.config or cfg_arq, os.path.join(tmp, "config.json"))
        caminhos.ARQ_BANCO = os.path.join(tmp, "radar.sqlite3")
        caminhos.ARQ_CONFIG = os.path.join(tmp, "config.json")
        caminhos.DADOS = caminhos.SONDA = os.path.join(tmp, "dados")
        testar()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("testar_avisos: %d falha(s)" % len(FALHAS))
    sys.exit(1 if FALHAS else 0)


def testar():
    from radar.banco import Banco
    from radar.notificador import Notificador
    b = Banco()
    base = config.carregar()
    dmin = base["alerta"].get("desconto_minimo", 0)

    def cfg_com(**tipos):
        c = copy.deepcopy(base)
        c["alerta"]["tipos"] = {"selo": False, "novo": False, "igual": False, "24m": False, **tipos}
        return c

    print("== Aceite 2: só o Selo ligado (banco de hoje)")
    so_selo = rodada(b, cfg_com(selo=True))
    oficiais = [x for x in so_selo if x.get("tag") not in ("keyshop", "completo")]
    print("  %d aviso(s): %s" % (len(so_selo), ", ".join("%s (%s, -%s%%)" % (x["nome"], x.get("tipo_oferta") or x.get("tag"),
                                                                            x.get("corte")) for x in so_selo) or "nenhum"))
    confere(all(x["selo"] and x["avisa_por"] == ["selo"] for x in oficiais), "todo aviso de loja oficial é Selo (G)")
    confere(all("favorito" not in x["motivo"] and "Raro" not in x["motivo"] for x in so_selo), "nenhum por raridade ou favorito")

    print("== Aceite 3: ligar/desligar Novo recorde")
    com_novo = rodada(b, cfg_com(selo=True, novo=True))
    novos = [x for x in com_novo if "novo" in (x.get("avisa_por") or [])]
    print("  com Novo recorde ligado: %d aviso(s), %d por novo recorde" % (len(com_novo), len(novos)))
    confere(bool(novos) and all(x["corte"] >= dmin and x["piso_tipo"] in ("novo", "raro") for x in novos),
            "Novo recorde ligado avisa novo com corte >= %d%%" % dmin)
    confere({x["appid"] for x in so_selo} == {x["appid"] for x in rodada(b, cfg_com(selo=True))}, "desligar volta ao que era")
    todos = rodada(b, cfg_com(selo=True, novo=True, igual=True, **{"24m": True}))
    confere(not any("24m" in x["avisa_por"] and x["corte"] < dmin for x in todos), "24m com corte < mínimo não avisa")
    al = {"tipos": {"novo": True}, "desconto_minimo": dmin}
    confere(analise.avisa_por(["selo", "novo"], dmin, al) == ["novo"], "Selo + novo recorde avisa com só Novo recorde ligado")
    confere(analise.avisa_por(["24m"], dmin - 1, {"tipos": {"24m": True}, "desconto_minimo": dmin}) == [], "24m abaixo do mínimo: não")

    print("== Aceite 4: ligar um tipo não dispara em massa")
    toasts = []
    notificar.mostrar = lambda titulo, texto, **k: toasts.append((titulo, texto))
    notificar.capa = lambda *a_: None  # sem rede
    b.con.execute("DELETE FROM notificado")
    b.meta("linha_de_base", "2026-01-01T00:00:00+00:00")
    b.meta("tipos_ligados", None)
    b.meta("pausado", False)
    c1 = cfg_com(selo=True)
    c1["notificacoes"]["silencio"]["ativo"] = False
    n1 = Notificador(b, c1, log=lambda *_: None)
    n1.processar(rodada(b, c1))  # 1a rodada da 0.15: grava tipos_ligados sem resumo
    toasts.clear()
    n1.processar(rodada(b, c1))
    confere(not toasts, "rodada seguinte com os mesmos tipos: nenhum toast")
    c2 = copy.deepcopy(c1)
    c2["alerta"]["tipos"]["novo"] = True
    al2 = rodada(b, c2)
    n_novo = sum(1 for x in al2 if x.get("avisa_por") == ["novo"])
    enviados = Notificador(b, c2, log=lambda *_: None).processar(al2)
    print("  ligou Novo recorde com %d jogo(s) já assim: %d toast(s): %s" % (n_novo, len(toasts), toasts))
    confere(len(toasts) == (1 if n_novo else 0) and not enviados, "1 toast de resumo e nenhum aviso individual")
    # alguem entra depois: tira um jogo do notificado (como se a promocao tivesse acabado e voltado)
    if n_novo:
        x = next(x for x in al2 if x.get("avisa_por") == ["novo"])
        b.con.execute("UPDATE notificado SET ativo=0 WHERE appid=?", (x["appid"],))
        toasts.clear()
        env = Notificador(b, c2, log=lambda *_: None).processar(rodada(b, c2))
        confere([e["appid"] for e in env] == [x["appid"]] and toasts and toasts[0][0].startswith("Novo recorde · "),
                "quem entra depois avisa normalmente (título \"%s\")" % (toasts[0][0] if toasts else "?"))
    b.con.close()


if __name__ == "__main__":
    main()
