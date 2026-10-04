"""Testes sinteticos (sem rede, sem banco) da pilula de piso, do Lendario, do Selo (so G) e de "Costuma voltar".
Uso: py tools/testar_piso.py  -> imprime so as falhas e o total; sai com 1 se algo falhou."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar.analise import analisar, costuma_voltar, tipos_de  # noqa: E402

AGORA = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
MES = 30.44
CHEIO = 10000


def iso(meses_atras, dias=0):
    return (AGORA - timedelta(days=meses_atras * MES + dias)).isoformat()


def promo(meses_atras, preco, corte, dur=10):
    """Uma promocao de `dur` dias na Steam, voltando ao preco cheio."""
    return [dict(loja="Steam", preco=preco, corte=corte, quando=iso(meses_atras)),
            dict(loja="Steam", preco=CHEIO, corte=0, quando=iso(meses_atras, -dur))]


def rodar_caso(hist, preco, corte, inicio_meses=40, cfg_alerta=None):
    linhas = [dict(loja="Steam", preco=CHEIO, corte=0, quando=iso(inicio_meses))] + hist + \
             [dict(loja="Steam", preco=preco, corte=corte, quando=iso(0, 1))]
    r = analisar(linhas, preco, corte, agora_=AGORA.timestamp(), cfg_alerta=cfg_alerta)
    r["volta"] = costuma_voltar(r, corte)[0]
    r["tipos"] = tipos_de(r)
    return r


def mes_ano(meses_atras):
    return (AGORA - timedelta(days=meses_atras * MES)).strftime("%m/%Y")


# (nome, historico, preco atual, corte atual, campo, esperado, inicio do historico em meses)
mensal50 = lambda ate: [x for m in range(ate - 1, 1, -2) for x in promo(m, 5000, 50)]
CASOS = [
    # pilula de piso: os 18 meses contam desde a ULTIMA vez no nivel do recorde anterior
    ("recorde visto pela ultima vez ha 19 meses", promo(19, 5000, 50), 4500, 55, "piso_tipo", "raro", 40),
    ("recorde visto pela ultima vez ha 17 meses", promo(17, 5000, 50), 4500, 55, "piso_tipo", "novo", 40),
    ("preco atual = 50% do recorde", promo(2, 5000, 50), 2500, 75, "piso_tipo", "raro", 40),
    ("preco atual = 51% do recorde", promo(2, 5000, 50), 2550, 74, "piso_tipo", "novo", 40),
    # folga de centavos na metade (R$ 0,10 ou 1% da metade), como no "igual": caso real WRC 7 (04/10/2026)
    ("WRC 7: R$ 2,39 com recorde R$ 4,74 (metade R$ 2,37) -> raro", promo(2, 474, 90), 239, 95, "piso_tipo", "raro", 40),
    ("WRC 7: R$ 2,39 com recorde R$ 4,74 -> Selo", promo(2, 474, 90), 239, 95, "selo", True, 40),
    ("WRC 7: R$ 2,40 ainda e metade", promo(2, 474, 90), 240, 95, "selo", True, 40),
    ("metade + R$ 0,11 nao e metade", promo(2, 474, 90), 248, 95, "piso_tipo", "novo", 40),
    ("folga de 1% da metade (R$ 45,00 + 0,45): R$ 45,40 e metade", promo(2, 9000, 10), 4540, 55, "piso_tipo", "raro", 40),
    ("folga de 1% da metade: R$ 45,50 nao e", promo(2, 9000, 10), 4550, 55, "piso_tipo", "novo", 40),
    ("recorde de 30 meses revisto ha 17", promo(30, 5000, 50) + promo(17, 5000, 50), 4500, 55, "piso_tipo", "novo", 40),
    ("recorde de 30 meses revisto ha 19", promo(30, 5000, 50) + promo(19, 5000, 50), 4500, 55, "piso_tipo", "raro", 40),
    ("revisto ha 17 com centavos de diferenca", promo(30, 5000, 50) + promo(17, 5030, 50), 4500, 55, "piso_tipo", "novo", 40),
    ("igual ao recorde (centavos)", promo(19, 5000, 50), 5005, 50, "piso_tipo", "igual", 40),
    # Lendario (regra C): >= 24 meses de historico e >= 1 promocao anterior
    ("nunca chegou, 30 meses, promos anteriores", mensal50(30), 3000, 70, "nivel", "lendario", 30),
    ("nunca chegou, 18 meses -> Ultrarraro", mensal50(18), 3000, 70, "nivel", "ultrarraro", 18),
    ("nunca chegou, sem promo anterior -> Incomum", [], 3000, 70, "nivel", "incomum", 30),
    # 1a promocao <= 50% do preco cheio: a pilula diz Recorde raro, mas sem promocao anterior nao ha Selo (como o ARK)
    ("1a promo a -70%: pilula Recorde raro", [], 3000, 70, "piso_tipo", "raro", 30),
    ("1a promo a -70%: sem Selo", [], 3000, 70, "selo", False, 30),
    ("mesmo nivel todo mes -> Comum", mensal50(30), 5000, 50, "nivel", "comum", 30),
    # Selo Kurokami = so G (Recorde raro com promocao anterior; spec 04, 04/10). F (Lendario) nao da mais Selo.
    ("maior desconto da historia sem recorde raro -> sem Selo", mensal50(30), 3000, 70, "selo", False, 30),
    ("escada 40% -> 50% com 30 meses -> sem Selo", promo(24, 6000, 40) + promo(12, 6000, 40), 5000, 50, "selo", False, 30),
    ("escada 40% -> 50%: Lendario continua calculado", promo(24, 6000, 40) + promo(12, 6000, 40), 5000, 50, "nivel", "lendario", 30),
    ("recorde raro com promocao anterior -> Selo", promo(20, 5000, 50), 4500, 55, "selo", True, 40),
    ("Selo G (19 meses): motivo", promo(19, 5000, 50), 4500, 55, "selo_motivo", "o menor preço anterior (R$ 50,00) foi há 18 meses", 40),
    ("Selo G (50%): motivo", promo(2, 5000, 50), 2500, 75, "selo_motivo",
     "preço caiu pela metade ou mais (o menor anterior era R$ 50,00, %s)" % mes_ano(2), 40),
    # a data do texto e a do preco do recorde, nao a da ultima vez no nivel (WRC 7: R$ 4,74 em 07/2025, R$ 4,79 em 10/2026)
    ("metade: data do recorde, nao do nivel", promo(15, 474, 90) + promo(1, 479, 90), 239, 95, "selo_motivo",
     "preço caiu pela metade ou mais (o menor anterior era R$ 4,74, %s)" % mes_ano(15), 40),
    ("Selo + novo recorde: tipos", promo(20, 5000, 50), 4500, 55, "tipos", ["selo", "novo"], 40),
    ("recorde raro sem promo anterior conta como novo", [], 3000, 70, "tipos", ["novo"], 30),
    # "Costuma voltar" (so informa)
    ("volta: promo a cada 2 meses", mensal50(30), 5000, 50, "volta", "a cada ~2 meses", 30),
    ("volta: 1 vez por ano", promo(20, 5000, 50) + promo(8, 5000, 50), 5000, 50, "volta", "1 vez por ano", 30),
    ("volta: nunca teve (historico inteiro)", mensal50(30), 3000, 70, "volta", "nunca teve esse desconto", 30),
    ("volta: teve so antes dos 24 meses", promo(30, 3000, 70) + promo(10, 5000, 50), 3000, 70, "volta", "não teve nos últimos 2 anos", 40),
    ("volta: primeira promocao", [], 3000, 70, "volta", "primeira promoção", 30),
    ("volta: historico curto", [], 3000, 70, "volta", "histórico curto", 3),
    ("novo recorde comum nao ganha Selo", promo(17, 5000, 50), 4500, 55, "selo", False, 40),
    ("Ultrarraro (18 meses, sem recorde em R$) nao ganha Selo", mensal50(18) + promo(1, 2900, 71), 3000, 70, "selo", False, 18),
    ("Raro sozinho nao ganha Selo", promo(20, 5000, 50) + promo(8, 5000, 50), 5000, 50, "selo", False, 30),
    ("selo_corte_minimo 80 barra Selo de -70%", mensal50(30), 3000, 70, "selo", False, 30, {"selo_corte_minimo": 80}),
]


def rodar():
    falhas = []
    for nome, hist, preco, corte, campo, esperado, inicio, *cfg in CASOS:
        r = rodar_caso(hist, preco, corte, inicio, cfg[0] if cfg else None)
        if r[campo] != esperado:
            falhas.append("%s: %s=%r (esperado %r)" % (nome, campo, r[campo], esperado))
    return falhas


if __name__ == "__main__":
    f = rodar()
    for x in f:
        print("FALHOU " + x)
    print("testar_piso: %d/%d ok" % (len(CASOS) - len(f), len(CASOS)))
    sys.exit(1 if f else 0)
