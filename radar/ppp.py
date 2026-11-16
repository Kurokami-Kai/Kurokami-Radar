"""Preco regional (PPP) e teto de desconto esperado: base do Selo Kurokami (0.19).

- Preco PPP = preco cheio do jogo nos EUA (dolar) x moeda local por dolar pelo poder de compra. O fator vem do Banco
  Mundial (dado publico: consumo das familias, senao PIB) e pode ser trocado a mao em Configuracoes (`ppp.fator`).
  A tabela da Valve (Steamworks) nao entra: a pagina dela se diz confidencial.
- Teto esperado = o maior desconto que o jogo ja teve ou o desconto em que a franquia para (mediana do maior desconto
  dos jogos dela com 2 anos ou mais; pelo menos 2 jogos), o que for maior. Ex.: Forza Horizon 6 com -20% e a franquia
  parando em -50%: o teto e -50%.
- Piso PPP = preco PPP x (1 - teto). O Selo sai quando o preco chega nele ou quando o desconto chega pela 1a vez ao
  teto da franquia (`analise.analisar`, parametro `ppp`).
Coleta (pista lenta, 1x por dia, `coletar`): preco cheio em dolar da lista de desejos (Steam GetItems com pais US), o
fator do Banco Mundial e o maior desconto dos jogos das franquias que nao tem historico no Hunter (ITAD storelow)."""
import json
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import series
from .rede import lotes

WB = "https://api.worldbank.org/v2/country/%s/indicator/%s?format=json&per_page=10"
INDICADORES = ("PA.NUS.PRVT.PP", "PA.NUS.PPP")   # consumo das familias; PIB se o primeiro falhar
PADRAO = {"BR": 2.58}   # Banco Mundial, consumo das familias 2025; so se nunca deu para baixar
VALIDADE_FATOR = 30 * 86400   # o Banco Mundial publica 1 numero por ano
IDADE_FRANQUIA = 2 * 365 * 86400   # so jogos com 2 anos ou mais dizem onde a franquia para
VALIDADE_TETO = 30 * 86400


def _agora():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def baixar_fator(pais):
    """(valor, ano, indicador) do Banco Mundial ou None. Moeda local por dolar internacional."""
    for ind in INDICADORES:
        r = None
        for _ in range(2):   # o firewall do Banco Mundial segura alguns pedidos ate o timeout; outro tenta passa
            try:
                req = urllib.request.Request(WB % (urllib.parse.quote(pais), ind),
                                             headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    r = json.loads(resp.read().decode("utf-8"))
                break
            except Exception:
                time.sleep(2)
        serie = r[1] if isinstance(r, list) and len(r) > 1 and isinstance(r[1], list) else []
        for x in serie:   # do ano mais novo para o mais velho
            if x.get("value"):
                return round(float(x["value"]), 4), x.get("date"), ind
    return None


def fator(cfg, banco):
    """Moeda local por dolar pelo poder de compra: o de Configuracoes, senao o baixado, senao o padrao do pais."""
    manual = (cfg.get("ppp") or {}).get("fator")
    if manual:
        return float(manual)
    m = banco.meta("ppp_fator") or {}
    return m.get("valor") or PADRAO.get((cfg.get("pais") or "").upper())


def _lanc_ts(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def tetos_franquia(banco, cfg, agora_=None):
    """{appid da lista: (teto %, nome da franquia, n jogos)} pelo maior desconto dos OUTROS jogos da franquia com 2 anos
    ou mais (historico das lojas marcadas; sem historico, o storelow guardado em teto_jogo). Mediana; 2+ jogos."""
    agora_ = agora_ or time.time()
    J = {r["appid"]: r for r in banco.q("SELECT appid, nome, franquia, lancamento, na_lista, possuido FROM jogo "
                                         "WHERE tipo='jogo' AND (na_lista=1 OR possuido=1) AND nome IS NOT NULL")}
    if not J:
        return {}
    manual = {r["appid"]: r["nome"] for r in banco.q("SELECT appid, nome FROM franquia_manual")}
    fr = series.franquias([{"appid": a, "nome": j["nome"], "franquia": j["franquia"]} for a, j in J.items()], manual)
    lojas = [l for l in (cfg.get("lojas") or [])]
    if "Steam" in lojas:
        lojas.append("Steam (direto)")
    maxi = {}
    if lojas:
        for r in banco.q("SELECT appid, MAX(corte) c FROM preco WHERE corte>0 AND preco>0 AND loja IN (%s) GROUP BY appid"
                         % ",".join("?" * len(lojas)), *lojas):
            maxi[r["appid"]] = r["c"]
    for r in banco.q("SELECT appid, corte FROM teto_jogo"):
        if r["corte"] and r["corte"] > (maxi.get(r["appid"]) or 0):
            maxi[r["appid"]] = r["corte"]
    grupos = {}
    for a, nome in fr.items():
        grupos.setdefault(nome.lower(), []).append(a)
    out = {}
    for membros in grupos.values():
        for a in membros:
            if not J[a]["na_lista"] or J[a]["possuido"]:
                continue
            cortes = []
            for m in membros:
                ts = _lanc_ts(J[m]["lancamento"])
                if m != a and maxi.get(m) and ts and agora_ - ts >= IDADE_FRANQUIA:
                    cortes.append(maxi[m])
            if len(cortes) >= 2:
                out[a] = (int(statistics.median_low(cortes)), fr[a], len(cortes))
    return out


_CACHE = {"chave": None, "quando": 0, "mapa": {}}


def mapa(banco, cfg):
    """{appid da lista: {"usd", "fator", "teto_fr", "fr"}} para analise.analisar(ppp=...). Guardado por 10 min."""
    fx = fator(cfg, banco)
    chave = (fx, banco.meta("ppp_quando"), tuple(cfg.get("lojas") or ()))
    if _CACHE["chave"] == chave and time.time() - _CACHE["quando"] < 600:
        return _CACHE["mapa"]
    out = {}
    if fx:
        tetos = tetos_franquia(banco, cfg)
        for r in banco.q("SELECT appid, cheio_usd FROM jogo WHERE na_lista=1 AND cheio_usd > 0"):
            t = tetos.get(r["appid"])
            out[r["appid"]] = {"usd": r["cheio_usd"], "fator": fx, "teto_fr": t[0] if t else None,
                               "fr": t[1] if t else None}
    _CACHE.update(chave=chave, quando=time.time(), mapa=out)
    return out


def invalidar():
    _CACHE["chave"] = None


def coletar(cfg, banco, k_steam, k_itad, log=print):
    """Pista lenta, 1x por dia: preco cheio em dolar da lista, fator do Banco Mundial e teto de quem nao tem historico."""
    from . import steam
    wl = [r["appid"] for r in banco.q("SELECT appid FROM jogo WHERE na_lista=1 AND tipo='jogo'")]
    if wl:
        its = steam.get_items([{"appid": a} for a in wl], "US", chave=k_steam, log=log)
        n = 0
        for it in its:
            try:
                x = steam.normalizar_app(it)
            except Exception:
                continue
            if x.get("cheio_steam") is not None:
                banco.con.execute("UPDATE jogo SET cheio_usd=? WHERE appid=?", (x["cheio_steam"], x["appid"]))
                n += 1
        log("   PPP: preco em dolar de %d de %d jogos da lista" % (n, len(wl)))
    pais = (cfg.get("pais") or "BR").upper()
    m = banco.meta("ppp_fator") or {}
    try:
        idade = time.time() - datetime.fromisoformat(m["quando"]).timestamp()
    except (KeyError, TypeError, ValueError):
        idade = None
    if not m.get("valor") or idade is None or idade >= VALIDADE_FATOR:   # cada tentativa pode levar ate ~15 s
        f = baixar_fator(pais)
        if f:
            banco.meta("ppp_fator", {"valor": f[0], "ano": f[1], "indicador": f[2], "quando": _agora()})
            log("   PPP: %s por dolar pelo poder de compra (Banco Mundial, %s, %s)" % (str(f[0]).replace(".", ","), f[2], f[1]))
        else:
            log("   PPP: Banco Mundial nao respondeu; fica o fator anterior")
    if k_itad:
        try:
            _tetos_itad(cfg, banco, k_itad, log)
        except Exception as e:
            log("   PPP: teto das franquias pela ITAD falhou (%s)" % e)
    banco.meta("ppp_quando", _agora())
    banco.commit()
    invalidar()


def _tetos_itad(cfg, banco, k_itad, log):
    """Maior desconto (storelow das lojas marcadas) dos jogos de franquia da lista que o Hunter nao acompanha
    (biblioteca): sem isso, o FH5 que voce tem nao diria onde a franquia para."""
    from . import itad
    J = {r["appid"]: r for r in banco.q("SELECT appid, nome, franquia, na_lista FROM jogo WHERE tipo='jogo' "
                                         "AND (na_lista=1 OR possuido=1) AND nome IS NOT NULL")}
    manual = {r["appid"]: r["nome"] for r in banco.q("SELECT appid, nome FROM franquia_manual")}
    fr = series.franquias([{"appid": a, "nome": j["nome"], "franquia": j["franquia"]} for a, j in J.items()], manual)
    com_lista = {fr[a].lower() for a, j in J.items() if j["na_lista"]}
    tem_hist = {r["appid"] for r in banco.q("SELECT DISTINCT appid FROM preco WHERE corte>0")}
    limite = datetime.fromtimestamp(time.time() - VALIDADE_TETO, timezone.utc).isoformat()
    recentes = {r["appid"] for r in banco.q("SELECT appid FROM teto_jogo WHERE quando >= ?", limite)}
    alvo = [a for a in J if fr[a].lower() in com_lista and a not in tem_hist and a not in recentes]
    if not alvo:
        return
    pais = (cfg.get("pais") or "BR").upper()
    shops = sorted(itad.resolver_lojas(k_itad, pais, cfg.get("lojas") or [])[0])
    if not shops:
        return
    cache = banco.meta("itad_ids") or {}
    gids = itad.mapear(k_itad, alvo, cache, log)
    banco.meta("itad_ids", {**(banco.meta("itad_ids") or {}), **cache})
    por_gid = {g: a for a, g in gids.items()}
    q = _agora()
    n = 0
    for lote in lotes(list(por_gid), 200):
        r = itad._post("games/storelow/v2", k_itad, lote, country=pais, shops=",".join(map(str, shops))) or []
        for g in r:
            a = por_gid.get(g.get("id"))
            if not a:
                continue
            corte = max(((x.get("cut") or 0) for x in (g.get("lows") or [])), default=0)
            banco.con.execute("INSERT OR REPLACE INTO teto_jogo VALUES(?,?,?)", (a, corte, q))
            n += 1
    for a in alvo:   # sem resposta da ITAD: nao pergunta de novo por 30 dias
        if a not in gids:
            banco.con.execute("INSERT OR REPLACE INTO teto_jogo VALUES(?,?,?)", (a, 0, q))
    log("   PPP: maior desconto de %d jogos de franquia sem historico (ITAD)" % n)
