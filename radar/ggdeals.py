"""GG.deals: melhor preco oficial e de keyshop + menores historicos de cada um.
Os dados da GG.deals atualizam de hora em hora, entao nao adianta consultar mais que isso.
Termos da API gratuita: uso pessoal e credito com link para a GG.deals onde os dados aparecem."""
import urllib.error
import urllib.parse

from .rede import RITMO, de_reais, http_json, lotes

API = "https://api.gg.deals/v1/prices/by-steam-app-id/"


class ChaveRecusada(Exception):
    pass


def precos(chave, appids, regiao="br", log=print):
    from . import progresso
    saida = {}
    tot = len(set(appids))
    for n, lote in enumerate(lotes(sorted(set(appids)), 100), 1):
        progresso.passo(min(n * 100, tot), tot)
        url = API + "?" + urllib.parse.urlencode({"ids": ",".join(map(str, lote)), "key": chave, "region": regiao})
        try:
            r = http_json(url, ritmo=RITMO["gg"]) or {}
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ChaveRecusada("a GG.deals recusou a chave (HTTP %d)" % e.code)
            log("   lote %d da GG.deals falhou (HTTP %d), seguindo" % (n, e.code))
            continue
        except Exception as e:
            log("   lote %d da GG.deals falhou (%s), seguindo" % (n, e))
            continue
        dados = r.get("data") if isinstance(r, dict) else None
        for k, v in (dados or {}).items():
            if not isinstance(v, dict):
                continue
            p = v.get("prices") or {}
            saida[int(k)] = {
                "oficial": de_reais(p.get("currentRetail")), "keyshop": de_reais(p.get("currentKeyshops")),
                "hist_oficial": de_reais(p.get("historicalRetail")), "hist_keyshop": de_reais(p.get("historicalKeyshops")),
                "moeda": p.get("currency"), "url": v.get("url"),
            }
    return saida
