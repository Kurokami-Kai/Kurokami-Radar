"""Ficha do jogo (spec 09): o que so a ficha usa. Buscado ao abrir (nunca na coleta) e guardado em ficha_cache:
descricao, captura de tela e informacoes da loja (appdetails), tempo para zerar, jogadores e notas (Augmented Steam,
servico de terceiro sem contrato: se falhar, a ficha abre sem o quadro) e as conquistas da conta. O HLTB de uma franquia
inteira vem junto ao abrir a ficha da franquia (hltb_lote, ate 60 jogos, o mesmo cache). Tambem a fileira
da franquia (so com os jogos que o Hunter conhece: biblioteca e lista) e o tempo jogado (gravado pela coleta)."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import credenciais, series, steam
from .banco import agora
from .rede import http_json

AUGMENTED = "https://api.augmentedsteam.com/app/%d/v2"
VALIDADE = {"loja": timedelta(days=30), "aug": timedelta(days=30), "conq": timedelta(hours=6)}
VALIDADE_FALHA = timedelta(hours=1)   # fonte fora do ar: tenta de novo depois, sem martelar a cada ficha aberta
VALIDADE_VAZIO = timedelta(days=1)    # respondeu sem nada (jogo novo, "em breve"): olha de novo amanha, nao em 30 dias


def _do_cache(b, a, fonte):
    r = b.um("SELECT dados, quando FROM ficha_cache WHERE appid=? AND fonte=?", a, fonte)
    if not r:
        return None
    d = json.loads(r["dados"])
    idade = datetime.now(timezone.utc) - datetime.fromisoformat(r["quando"])
    validade = VALIDADE_FALHA if d.get("falhou") else VALIDADE_VAZIO if d.get("vazio") else VALIDADE[fonte]
    return d if idade < validade else None


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _url(v):
    """Servico de terceiro sem contrato: so link https vai para a pagina."""
    return v if isinstance(v, str) and v.startswith("https://") else None


def augmented(appid):
    """HLTB em minutos (FF VII Remake: 1935 = 32 h, como no site), jogadores e notas de usuarios/criticos."""
    r = http_json(AUGMENTED % appid, tentativas=2, timeout=15) or {}
    h, rv, p = r.get("hltb") or {}, r.get("reviews") or {}, r.get("players") or {}
    hl = {k: _num(h.get(k)) or None for k in ("story", "extras", "complete")}
    meta, oc = rv.get("metauser") or {}, rv.get("opencritic") or {}
    return {"hltb": hl if any(hl.values()) else None, "hltb_url": _url(h.get("url")),
            "meta": _num(meta.get("score")), "meta_url": _url(meta.get("url")),
            "oc": _num(oc.get("score")), "oc_url": _url(oc.get("url")),
            "jogando": _num(p.get("recent")), "pico_hoje": _num(p.get("peak_today")), "pico": _num(p.get("peak_all"))}


def extras(b, cfg, a, tenho, log_erro=None):
    """{loja, aug, conq}: do cache ou buscados em paralelo (o que faltar ou venceu). Fonte que falhou vem None."""
    fontes = {"loja": lambda: steam.detalhes_loja(a, cfg["pais"]), "aug": lambda: augmented(a)}
    chave, sid = credenciais.ler("steam"), b.meta("steamid")
    if tenho and chave and sid:
        fontes["conq"] = lambda: steam.conquistas(chave, sid, a)
    out, buscar = {}, {}
    for f, fn in fontes.items():
        c = _do_cache(b, a, f)
        if c is None:
            buscar[f] = fn
        else:
            out[f] = c
    if buscar:
        with ThreadPoolExecutor(len(buscar)) as ex:
            fut = {f: ex.submit(fn) for f, fn in buscar.items()}
        for f, fu in fut.items():
            try:
                out[f] = fu.result() or {}
                if not any(v for v in out[f].values()):
                    out[f] = {"vazio": True}
            except Exception as e:
                out[f] = {"falhou": str(e)[:200]}
        try:
            b.con.executemany("INSERT OR REPLACE INTO ficha_cache VALUES(?,?,?,?)",
                              [(a, f, json.dumps(out[f]), agora()) for f in buscar])
            b.commit()
        except Exception as e:   # banco ocupado pela coleta: a ficha mostra o que buscou, sem guardar
            b.con.rollback()
            if log_erro:
                log_erro("cache da ficha", e)
    return {f: (None if d.get("falhou") else d) for f, d in out.items()}


def hltb_lote(b, appids, log_erro=None, maximo=60):
    """{appid: {story, extras, complete} em minutos, ou None}: o HLTB de varios jogos (ficha da franquia), do mesmo
    cache da ficha; os que faltam vem do Augmented Steam em paralelo (no maximo `maximo` por pedido)."""
    out, buscar = {}, []
    for a in appids:
        c = _do_cache(b, a, "aug")
        if c is None:
            buscar.append(a)
        else:
            out[a] = c.get("hltb")
    buscar = buscar[:maximo]
    if buscar:
        with ThreadPoolExecutor(6) as ex:
            fut = {a: ex.submit(augmented, a) for a in buscar}
        novos = []
        for a, fu in fut.items():
            try:
                d = fu.result() or {}
                if not any(v for v in d.values()):
                    d = {"vazio": True}
            except Exception as e:
                d = {"falhou": str(e)[:200]}
            out[a] = d.get("hltb")
            novos.append((a, "aug", json.dumps(d), agora()))
        try:
            b.con.executemany("INSERT OR REPLACE INTO ficha_cache VALUES(?,?,?,?)", novos)
            b.commit()
        except Exception as e:   # banco ocupado pela coleta: responde sem guardar
            b.con.rollback()
            if log_erro:
                log_erro("cache do HLTB", e)
    return out


def jogado(b, a):
    r = b.um("SELECT minutos, ultima FROM tempo_jogo WHERE appid=?", a)
    return {"minutos": r["minutos"], "ultima": r["ultima"]} if r else None


def fileira(b, ctx, a, nome, marcadas):
    """A franquia do jogo entre os que o Hunter conhece (biblioteca e lista), em ordem de lancamento, com o preco de
    agora (lojas marcadas) dos que voce nao tem. "nomes": as franquias com 2+ jogos, para o "trocar" da ficha."""
    J = ctx.jogos
    conhecidos = [x for x in ctx.possuidos | ctx.lista if (J.get(x) or {}).get("tipo") == "jogo" and J[x].get("nome")]
    itens = [{"appid": x, "nome": J[x]["nome"], "franquia": J[x].get("franquia")} for x in conhecidos]
    if a not in set(conhecidos):
        itens.append({"appid": a, "nome": nome or (J.get(a) or {}).get("nome") or str(a), "franquia": (J.get(a) or {}).get("franquia")})
    manual = {r["appid"]: r["nome"] for r in b.q("SELECT appid, nome FROM franquia_manual")}
    fr = series.franquias(itens, manual)
    alvo = fr[a]
    ids = [x["appid"] for x in itens if fr[x["appid"]].lower() == alvo.lower()]
    ofs = b.ofertas_atuais([x for x in ids if x not in ctx.possuidos])
    membros = []
    for x in ids:
        j = J.get(x) or {}
        vals = [o["preco"] for o in ofs.get(x, []) if o["loja"].lower() in marcadas and o["preco"] is not None]
        membros.append({"appid": x, "nome": j.get("nome") or nome, "capa": j.get("capa"), "capa_v": j.get("capa_v"),
                        "lancamento": j.get("lancamento"), "em_breve": bool(j.get("em_breve")),
                        "tenho": x in ctx.possuidos, "lista": x in ctx.lista,
                        "preco": None if x in ctx.possuidos else (min(vals) if vals else j.get("preco_steam"))})
    membros.sort(key=lambda m: (m["lancamento"] is None, m["lancamento"] or 0))   # sem data (em breve) no fim
    grafia, conta = {}, {}
    for n in fr.values():
        grafia.setdefault(n.lower(), n)
        conta[n.lower()] = conta.get(n.lower(), 0) + 1
    return {"nome": alvo, "manual": a in manual, "tenho": sum(1 for m in membros if m["tenho"]), "total": len(membros),
            "membros": membros, "nomes": sorted((grafia[k] for k, c in conta.items() if c > 1), key=str.lower)}
