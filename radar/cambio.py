"""Câmbio para o histórico da ITAD.
A ITAD devolve o histórico (games/history/v2) no dinheiro de cada loja (Humble, Fanatical, GamesPlanet, IndieGala...
em US$, € e £) e só os preços de agora (games/prices/v3) já convertidos para o país. Sem converter, US$ 3,99 virava
R$ 3,99 e o "menor preço" dessas lojas ficava 5x abaixo do real. A taxa de hoje vale para o histórico inteiro (a da
ITAD para os preços de agora também é a de hoje). Taxas do Frankfurter (Banco Central Europeu, sem chave), guardadas em
dados/cambio.json por 24 h; sem rede, a última guardada, e sem nada, a tabela FALLBACK."""
import json
import os
import threading
import time

from . import caminhos
from .rede import http_json

URL = "https://api.frankfurter.dev/v1/latest?base=BRL"
VALIDADE = 24 * 3600
FALLBACK = {"USD": 5.0, "EUR": 5.6, "GBP": 6.6}      # reais por unidade (outubro de 2026), só se nunca houve rede
MOEDA_PAIS = {"BR": "BRL"}                           # país sem conversão: o histórico segue como a ITAD manda
_TRAVA = threading.Lock()
_MEMORIA = {"quando": 0.0, "taxas": None}


def moeda_do_pais(pais):
    return MOEDA_PAIS.get(str(pais or "").upper())


def _arquivo():
    return os.path.join(caminhos.DADOS, "cambio.json")


def _ler():
    try:
        with open(_arquivo(), encoding="utf-8") as f:
            d = json.load(f)
        return float(d["quando"]), {k: float(v) for k, v in d["taxas"].items()}
    except (OSError, ValueError, KeyError, TypeError):
        return 0.0, None


def _baixar():
    """Reais por unidade de cada moeda (a API dá moedas por real; inverte). None se a rede falhar."""
    try:
        r = http_json(URL, tentativas=2, timeout=15)
        taxas = {m: 1.0 / v for m, v in ((r or {}).get("rates") or {}).items() if v}
    except Exception:
        return None
    return taxas or None


def taxas():
    """{moeda: reais por unidade}. Cache em memória e em disco por 24 h; nunca levanta erro."""
    with _TRAVA:
        agora = time.time()
        if _MEMORIA["taxas"] and agora - _MEMORIA["quando"] < VALIDADE:
            return _MEMORIA["taxas"]
        quando, guardadas = _ler()
        if guardadas and agora - quando < VALIDADE:
            _MEMORIA.update(quando=quando, taxas=guardadas)
            return guardadas
        novas = _baixar()
        if novas:
            try:
                os.makedirs(caminhos.DADOS, exist_ok=True)
                with open(_arquivo(), "w", encoding="utf-8") as f:
                    json.dump({"quando": agora, "taxas": novas}, f)
            except OSError:
                pass
            _MEMORIA.update(quando=agora, taxas=novas)
            return novas
        t = guardadas or dict(FALLBACK)
        _MEMORIA.update(quando=agora - VALIDADE + 600, taxas=t)   # sem rede: tenta de novo em 10 min
        return t


def em_reais(valor, moeda, alvo="BRL"):
    """Valor decimal na `moeda` para a moeda do país (alvo). Igual ao alvo ou sem moeda: devolve como veio.
    Moeda sem taxa: None (melhor perder o registro do que gravar US$ como R$)."""
    if valor is None or not moeda or moeda == alvo or alvo != "BRL":
        return valor
    t = taxas().get(moeda)
    return valor * t if t else None
