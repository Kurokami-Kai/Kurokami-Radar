"""Teste de viabilidade de "promocoes da Steam inteira" no Brasil (spec 04, Etapa 1.6). So LE: nao grava no banco.

Uso: py tools/teste_promocoes_steam.py [--fontes itad,itad_todas,steam,busca] [--max-chamadas 1000] [--max-min 15]
Feche o Radar antes (a chave da ITAD e a mesma). Usa rede.http_json (ritmo e backoff) e a chave do keyring.
Fontes, nesta ordem:
  itad        ITAD deals/v2, country=BR, so a loja Steam (shops=61), 200 por chamada; + lookup/shop/61/id/v1 (appids)
  itad_todas  o mesmo com todas as lojas (sem mapear appids)
  steam       IStoreQueryService/Query/v1 sem chave: apps + DLCs com min_discount_percent=1, country_code=BR, sort=2
  busca       store.steampowered.com/search/results/?specials=1&cc=br&json=1 (pagina, nao API: ultimo recurso)
Para em --max-chamadas ou --max-min por fonte e extrapola pelo total informado pela fonte.
Resumo em dados/sonda/promocoes_steam.json (fora do Git), com os appids de cada fonte para comparar."""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import caminhos, credenciais, rede  # noqa: E402
from radar.rede import RITMO, http_json  # noqa: E402

ITAD = "https://api.isthereanydeal.com/"
QUERY = "https://api.steampowered.com/IStoreQueryService/Query/v1/"
BUSCA = "https://store.steampowered.com/search/results/"

# ---- medidor: bytes baixados, chamadas e 429 (embrulha o urlopen e o freio do ritmo que o rede.py usa)
MED = {"chamadas": 0, "bytes": 0, "429": 0, "erros": 0}
_urlopen = urllib.request.urlopen
_freio = rede.Ritmo.freio


class _Resp:
    def __init__(self, r):
        self.r = r

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.r.close()

    def read(self, *a):
        d = self.r.read(*a)
        MED["bytes"] += len(d)
        return d


def _contar_urlopen(*a, **k):
    MED["chamadas"] += 1
    return _Resp(_urlopen(*a, **k))


def _contar_freio(self, *a, **k):
    MED["429"] += 1
    return _freio(self, *a, **k)


urllib.request.urlopen = _contar_urlopen
rede.Ritmo.freio = _contar_freio


class Fonte:
    def __init__(self, nome, max_ch, max_s):
        self.nome, self.max_ch, self.max_s = nome, max_ch, max_s
        self.t0, self.m0 = time.time(), dict(MED)
        self.itens, self.total_informado, self.parou, self.campos, self.obs = 0, None, None, {}, []
        self.appids, self.tipos = set(), Counter()

    def pode(self):
        if MED["chamadas"] - self.m0["chamadas"] >= self.max_ch:
            self.parou = "limite de %d chamadas" % self.max_ch
        elif time.time() - self.t0 >= self.max_s:
            self.parou = "limite de %d min" % (self.max_s // 60)
        return not self.parou

    def resumo(self):
        ch = MED["chamadas"] - self.m0["chamadas"]
        s = time.time() - self.t0
        mb = (MED["bytes"] - self.m0["bytes"]) / 1e6
        r = {"fonte": self.nome, "chamadas": ch, "itens_lidos": self.itens, "itens_por_chamada": round(self.itens / ch, 1) if ch else 0,
             "tempo_s": round(s), "mb": round(mb, 1), "recusas_429": MED["429"] - self.m0["429"],
             "erros": MED["erros"] - self.m0["erros"], "total_informado": self.total_informado, "parou": self.parou,
             "tipos": dict(self.tipos), "appids_distintos": len(self.appids), "campos": self.campos, "obs": self.obs}
        if self.parou and self.total_informado and self.itens:
            f = self.total_informado / self.itens
            r["extrapolado"] = {"chamadas": round(ch * f), "tempo_min": round(s * f / 60, 1), "mb": round(mb * f)}
        return r


def _itad_get(caminho, chave, **params):
    params["key"] = chave
    return http_json(ITAD + caminho + "?" + urllib.parse.urlencode(params, doseq=True), ritmo=RITMO["itad"])


def fonte_itad(chave, so_steam, a):
    f = Fonte("itad" + ("" if so_steam else "_todas"), a.max_chamadas, a.max_min * 60)
    params = {"country": "BR", "limit": 200}
    if so_steam:
        params["shops"] = "61"
    offset, ids, flags, lojas = 0, [], Counter(), Counter()
    hl = Counter()
    while f.pode():
        try:
            r = _itad_get("deals/v2", chave, offset=offset, **params) or {}
        except Exception as e:
            MED["erros"] += 1; f.obs.append("deals/v2 offset %d: %s" % (offset, rede.explicar(e))); break
        lst = r.get("list") or []
        if offset == 0 and lst:
            f.campos = {"item": sorted(lst[0]), "deal": sorted(lst[0].get("deal") or {})}
        for it in lst:
            d = it.get("deal") or {}
            f.itens += 1; f.tipos[it.get("type")] += 1
            ids.append(it["id"]); flags[d.get("flag")] += 1; lojas[(d.get("shop") or {}).get("name")] += 1
            p = (d.get("price") or {}).get("amountInt")
            h1 = (d.get("historyLow_1y") or {}).get("amountInt")
            h = (d.get("historyLow") or {}).get("amountInt")
            if p is not None and h is not None:
                hl["abaixo_do_menor"] += p < h; hl["igual_ao_menor"] += p == h
            if p is not None and h1 is not None:
                hl["igual_ou_abaixo_menor_12m"] += p <= h1
            hl["com_expiry"] += bool(d.get("expiry"))
        offset = r.get("nextOffset") or offset + len(lst)
        if not r.get("hasMore") or not lst:
            f.total_informado = f.itens
            break
    if f.parou:
        f.obs.append("hasMore ainda verdadeiro em offset %d; total desconhecido" % offset)
    f.obs.append("flags (N novo recorde, H no recorde, S recorde da loja): %s" % dict(flags))
    f.obs.append("contagens: %s" % dict(hl))
    if not so_steam:
        f.obs.append("lojas (melhor oferta por jogo): %s" % dict(lojas.most_common(12)))
    out = f.resumo()
    if so_steam and ids:  # quanto custa saber o appid de cada jogo
        g = Fonte("itad_lookup_appid", a.max_chamadas, a.max_min * 60)
        for i in range(0, len(ids), 200):
            if not g.pode():
                break
            try:
                r = http_json(ITAD + "lookup/shop/61/id/v1?" + urllib.parse.urlencode({"key": chave}),
                              corpo=ids[i:i + 200], ritmo=RITMO["itad"]) or {}
            except Exception as e:
                MED["erros"] += 1; g.obs.append("lookup %d: %s" % (i, rede.explicar(e))); break
            for v in r.values():
                g.itens += 1
                app = next((int(x[4:]) for x in v or [] if x.startswith("app/")), None)
                if app:
                    g.appids.add(app)
        g.total_informado = len(ids)
        out["lookup_appid"] = g.resumo()
        out["appids"] = sorted(g.appids)
    return out


def fonte_steam(a):
    f = Fonte("steam", a.max_chamadas, a.max_min * 60)
    n, start = 1000, 0
    # sem "sort" a ordem muda entre chamadas e a paginacao repete/pula itens; 1, 2 e 13 deram ordem estavel
    pedido = {"query": {"start": 0, "count": n, "sort": 2, "filters": {
        "type_filters": {"include_apps": True, "include_dlc": True}, "price_filters": {"min_discount_percent": 1}}},
        "context": {"language": "brazilian", "country_code": "BR"},
        "data_request": {"include_release": True, "include_reviews": True}}
    cheio = dict(pedido["data_request"], include_basic_info=True, include_assets=True, include_all_purchase_options=True)
    fim, cortes = Counter(), Counter()
    while f.pode():
        pedido["query"]["start"] = start
        dr = pedido["data_request"]
        if start == 0:  # a primeira chamada pede tudo, so para listar os campos
            pedido["data_request"] = cheio
        try:
            r = (http_json(QUERY + "?" + urllib.parse.urlencode({"input_json": json.dumps(pedido)}), ritmo=RITMO["steam"])
                 or {}).get("response") or {}
        except Exception as e:
            MED["erros"] += 1; f.obs.append("start %d: %s" % (start, rede.explicar(e))); break
        finally:
            pedido["data_request"] = dr
        f.total_informado = (r.get("metadata") or {}).get("total_matching_records", f.total_informado)
        its = r.get("store_items") or []
        if start == 0 and its:
            f.campos = {"item (pedido completo)": sorted(its[0]), "best_purchase_option": sorted(its[0].get("best_purchase_option") or {})}
        for it in its:
            f.itens += 1; f.tipos[it.get("type")] += 1; f.appids.add(it.get("appid") or it.get("id"))
            b = it.get("best_purchase_option") or {}
            cortes["com_corte" if b.get("discount_pct") else "sem_corte"] += 1
            fim["com_fim"] += any(d.get("discount_end_date") for d in b.get("active_discounts") or [])
        if not its:
            if start < (f.total_informado or 0):
                f.obs.append("parou de devolver itens em start %d (total informado %s)" % (start, f.total_informado))
            break
        start += len(its)
        if start >= (f.total_informado or 0):
            break
    f.obs.append("tipos: 0=jogo, 4=DLC (EStoreAppType); %s · %s" % (dict(cortes), dict(fim)))
    out = f.resumo()
    out["appids"] = sorted(x for x in f.appids if x)
    return out


def fonte_busca(a):
    f = Fonte("busca", a.max_chamadas, a.max_min * 60)
    start = 0
    while f.pode():
        url = BUSCA + "?" + urllib.parse.urlencode({"specials": 1, "cc": "br", "l": "brazilian", "json": 1,
                                                    "start": start, "count": 100, "infinite": 1})
        try:
            r = http_json(url, ritmo=RITMO["loja"]) or {}
        except Exception as e:
            MED["erros"] += 1; f.obs.append("start %d: %s" % (start, rede.explicar(e))); break
        f.total_informado = r.get("total_count", f.total_informado)
        html = r.get("results_html") or ""
        linhas = re.findall(r'data-ds-itemkey="([A-Za-z]+)_\d+"', html)  # App_123, Sub_456, Bundle_789
        ids = re.findall(r'data-ds-appid="(\d+)"', html)  # pacotes trazem "1,2,3" e ficam de fora
        if start == 0:
            f.campos = {"json": sorted(r), "html": sorted(set(re.findall(r'class="(search_[a-z_]+)', html)))}
        if not linhas:
            break
        f.itens += len(linhas); f.tipos.update(linhas); f.appids.update(int(x) for x in ids)
        start += len(linhas)  # a pagina avanca por linha (app, pacote ou bundle)
        if start >= (f.total_informado or 0):
            break
    f.obs.append("appid, nome, capa, lancamento, nota (tooltip), % e precos em HTML; tipo e fim do desconto nao vem")
    out = f.resumo()
    out["appids"] = sorted(f.appids)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fontes", default="itad,itad_todas,steam,busca")
    ap.add_argument("--max-chamadas", type=int, default=1000)
    ap.add_argument("--max-min", type=int, default=15)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    res = {"gerado": datetime.now(timezone.utc).isoformat(), "fontes": []}
    for nome in a.fontes.split(","):
        print("== %s" % nome, flush=True)
        if nome.startswith("itad"):
            chave = credenciais.ler("itad")
            if not chave:
                print("   sem chave da ITAD no keyring; pulando"); continue
            r = fonte_itad(chave, nome == "itad", a)
        else:
            r = {"steam": fonte_steam, "busca": fonte_busca}[nome](a)
        res["fontes"].append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "appids"} | (
            {"lookup_appid": {k: v for k, v in r["lookup_appid"].items() if k != "appids"}} if "lookup_appid" in r else {}),
            ensure_ascii=False, indent=1), flush=True)
    conj = {r["fonte"]: set(r.get("appids") or []) for r in res["fontes"] if r.get("appids")}
    if len(conj) > 1:
        nomes = sorted(conj)
        res["sobreposicao"] = {"%s&%s" % (x, y): len(conj[x] & conj[y]) for i, x in enumerate(nomes) for y in nomes[i + 1:]}
        print("sobreposicao de appids:", res["sobreposicao"])
    pasta = os.path.join(caminhos.BASE, "dados", "sonda")
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, "promocoes_steam.json"), "w", encoding="utf-8") as fp:
        json.dump(res, fp, ensure_ascii=False)


if __name__ == "__main__":
    main()
