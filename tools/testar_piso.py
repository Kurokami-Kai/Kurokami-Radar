"""Testes sinteticos (sem rede, sem banco) da pilula de piso e do Lendario.
Uso: py tools/testar_piso.py  -> imprime so as falhas e o total; sai com 1 se algo falhou."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar.analise import analisar  # noqa: E402

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
    return analisar(linhas, preco, corte, agora_=AGORA.timestamp(), cfg_alerta=cfg_alerta)


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
    ("recorde de 30 meses revisto ha 17", promo(30, 5000, 50) + promo(17, 5000, 50), 4500, 55, "piso_tipo", "novo", 40),
    ("recorde de 30 meses revisto ha 19", promo(30, 5000, 50) + promo(19, 5000, 50), 4500, 55, "piso_tipo", "raro", 40),
    ("revisto ha 17 com centavos de diferenca", promo(30, 5000, 50) + promo(17, 5030, 50), 4500, 55, "piso_tipo", "novo", 40),
    ("igual ao recorde (centavos)", promo(19, 5000, 50), 5005, 50, "piso_tipo", "igual", 40),
    # Lendario (regra C): >= 24 meses de historico e >= 1 promocao anterior
    ("nunca chegou, 30 meses, promos anteriores", mensal50(30), 3000, 70, "nivel", "lendario", 30),
    ("nunca chegou, 18 meses -> Ultrarraro", mensal50(18), 3000, 70, "nivel", "ultrarraro", 18),
    ("nunca chegou, sem promo anterior -> Incomum", [], 3000, 70, "nivel", "incomum", 30),
    # 1a promocao <= 50% do preco cheio: Recorde raro pela regra G como foi escrita (decisao pendente, ver decisoes.md)
    ("1a promo a -70%: Recorde raro (G)", [], 3000, 70, "selo_motivo", "menor preço desde " + mes_ano(30), 30),
    ("mesmo nivel todo mes -> Comum", mensal50(30), 5000, 50, "nivel", "comum", 30),
    # Selo Kurokami = F (Lendario) ou G (Recorde raro); Raro e Ultrarraro sozinhos nao
    ("Selo F: Lendario", mensal50(30), 3000, 70, "selo_motivo", "maior desconto da história (-70%; antes, no máximo -50%)", 30),
    ("Selo G: Recorde raro (19 meses)", promo(19, 5000, 50), 4500, 55, "selo_motivo", "menor preço desde " + mes_ano(40), 40),
    ("Selo G: Recorde raro (50%)", promo(2, 5000, 50), 2500, 75, "selo", True, 40),
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
