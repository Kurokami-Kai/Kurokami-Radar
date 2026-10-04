"""Painel local: servidor HTTP so em 127.0.0.1, com API JSON lendo o banco e a pagina painel.html."""
import json
import os
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import re
import urllib.parse as _up

from . import VERSAO, analise, caminhos, config, dlc as dlcmod, steam
from .rede import http_json
from .banco import Banco

PORTAS = (80, 8787)       # tenta a 80 (link sem numero); se estiver ocupada, usa a 8787
PORTA = 8787              # a que ficou valendo
CAMINHO = "/kurokami"
ARQ_TOKEN = os.path.join(caminhos.DADOS, "painel_token.txt")
TENTATIVAS = {}           # ip -> [horarios], limita chutes de PIN
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel.html")
CONTROLE = {"servico": None, "srv": None}  # preenchido pela bandeja


def token(novo=False):
    import secrets
    caminhos.garantir()
    if not novo and os.path.isfile(ARQ_TOKEN):
        with open(ARQ_TOKEN, encoding="utf-8") as f:
            t = f.read().strip()
        if t.isdigit() and len(t) == 6:
            return t
    t = "%06d" % secrets.randbelow(10 ** 6)  # PIN de 6 digitos: facil de digitar no celular
    with open(ARQ_TOKEN, "w", encoding="utf-8") as f:
        f.write(t)
    return t


def ips_locais():
    import socket
    ips = set()
    try:
        s_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_.connect(("8.8.8.8", 80))
        ips.add(s_.getsockname()[0])
        s_.close()
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    return sorted(ips, key=lambda i: (not i.startswith("192.168."), i))


def _base(host):
    return "http://%s%s" % (host, "" if PORTA == 80 else ":%d" % PORTA)


def rede_local():
    return bool((config.carregar().get("painel") or {}).get("rede_local"))
NAO_LOJA = {analise.LOJA_COMPLETO, analise.LOJA_GG_OFICIAL, analise.LOJA_GG_KEYSHOP, "Steam (direto)"}


def _fim(oferta, jogo):
    """Quando a promocao acaba (epoch), pela ITAD ou pela Steam."""
    if oferta and oferta.get("expira"):
        try:
            return int(datetime.fromisoformat(str(oferta["expira"]).replace("Z", "+00:00")).timestamp())
        except ValueError:
            pass
    if oferta and oferta.get("loja") == "Steam" and (oferta.get("corte") or 0) > 0:
        return (jogo or {}).get("fim_desconto")
    return None


def _marcadas(cfg):
    return {l.lower() for l in cfg["lojas"]}


def _ultimos_por_loja(b, appids=None):
    filtro = "WHERE appid IN (SELECT appid FROM jogo WHERE na_lista=1)" if appids is None else \
        "WHERE appid IN (%s)" % ",".join(str(int(a)) for a in appids)
    return b.q("""SELECT p.appid, p.loja, p.preco, p.cheio, p.corte, p.url, p.quando FROM preco p
                  JOIN (SELECT appid, loja, MAX(quando) mq FROM preco %s GROUP BY appid, loja) u
                  ON p.appid=u.appid AND p.loja=u.loja AND p.quando=u.mq""" % filtro)


def _minimos(b, appids=None):
    filtro = "WHERE appid IN (SELECT appid FROM jogo WHERE na_lista=1)" if appids is None else \
        "WHERE appid IN (%s)" % ",".join(str(int(a)) for a in appids)
    return b.q("SELECT appid, loja, COALESCE(MIN(CASE WHEN preco>0 THEN preco END), MIN(preco)) m FROM preco %s GROUP BY appid, loja" % filtro)


def _idade_userdata():
    import time
    arq = caminhos.achar_userdata(config.carregar())
    return int((time.time() - os.path.getmtime(arq)) / 86400) if arq else None


def api_resumo(_q):
    b = Banco()
    s = CONTROLE["servico"]
    ult = b.meta("ultimos_alertas") or {}
    r = {"versao": VERSAO, "na_lista": b.um("SELECT COUNT(*) n FROM jogo WHERE na_lista=1")["n"],
         "possuidos": b.um("SELECT COUNT(*) n FROM jogo WHERE possuido=1")["n"],
         "vale_a_pena": len(ult.get("itens") or []), "atualizado": ult.get("quando"),
         "pausado": bool(b.meta("pausado")), "na_bandeja": bool(s),
         "proxima": s.proxima.isoformat() if s else None, "estado": s.estado if s else None,
         "userdata_dias": _idade_userdata(), "atualizacao": CONTROLE.get("atualizacao"),
         "progresso": __import__("radar.progresso", fromlist=["x"]).foto(), "ult_completa": b.meta("ult_completa"),
         "completa_dias": config.carregar().get("verificacao_completa_dias", 7)}
    b.con.close()
    return r


def api_lista(_q):
    cfg = config.carregar()
    b = Banco()
    ctx = analise.Contexto(b, cfg)
    marc = _marcadas(cfg)
    mins = {}
    atuais = b.ofertas_atuais()
    for r in _minimos(b):
        mins.setdefault(r["appid"], {})[r["loja"]] = r["m"]
    lojas_m = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")} if l.lower() in marc]
    if "steam" in marc:
        lojas_m.append("Steam (direto)")
    linhas = b.linhas_lote(lojas_m)
    pisos = {a_: b._pisos_de(rs, (90, 180, 270, 365)) for a_, rs in linhas.items()}
    extras = {int(x) for x in (cfg.get("extras") or [])}
    mudos = {r["appid"] for r in b.q("SELECT appid FROM silenciado")}
    ult = b.meta("ultimos_alertas") or {}
    vale = {a["appid"]: a for a in (ult.get("itens") or [])}
    novos = set(ult.get("novos") or [])
    parciais = {r["appid"] for r in b.q("SELECT DISTINCT jo.appid FROM jogo_opcao jo JOIN opcao o ON o.id=jo.opcao WHERE o.papel='parcial'")}
    # a GG.deals le a edicao parcial nesses jogos (ex.: HITMAN), entao o keyshop dela nao vale
    gg = {r["appid"]: dict(r) for r in b.q("SELECT * FROM gg") if r["appid"] not in parciais}
    nb = {}
    for oid, o in ctx.opcoes.items():
        if o["tipo"] == "bundle":
            for a in o["itens"]:
                nb[a] = nb.get(a, 0) + 1
    out = []
    for a in ctx.lista:
        j = ctx.jogos.get(a) or {}
        if not j.get("nome"):
            continue
        ofs = [o for o in atuais.get(a, []) if o["loja"].lower() in marc]
        melhor = min(ofs, key=lambda o: o["preco"]) if ofs else None
        m = mins.get(a, {})
        piso_marc = min([v for k, v in m.items() if k.lower() in marc] or [None], key=lambda x: x if x is not None else 10**12)
        piso_geral = min([v for k, v in m.items() if k not in NAO_LOJA] or [None], key=lambda x: x if x is not None else 10**12)
        corte = melhor["corte"] if melhor else (j.get("desconto_steam") or 0)
        fim = _fim(melhor, j)
        ps = pisos.get(a) or {}
        tag, texto, acima = (analise.etiqueta(melhor["preco"], melhor.get("cheio"), ps, cfg["alerta"])
                             if melhor and melhor["corte"] else (None, None, None))
        an = analise.analisar(linhas.get(a, []), melhor["preco"] if melhor else None,
                              melhor["corte"] if melhor else 0, cfg_alerta=cfg["alerta"])
        preco = melhor["preco"] if melhor else j.get("preco_steam")
        cheio = (melhor or {}).get("cheio") or j.get("cheio_steam")
        g = gg.get(a) or {}
        modo = config.modo_do_jogo(cfg, a)
        out.append({
            "appid": a, "nome": j["nome"], "tipo": j.get("tipo"), "capa": j.get("capa"),
            "rpos": j.get("rpos") or 0, "rcount": j.get("rcount") or 0, "rotulo": j.get("rotulo") or "",
            "lancamento": j.get("lancamento"), "em_breve": j.get("em_breve"),
            "preco": preco, "cheio": cheio, "corte": corte or 0, "loja": melhor["loja"] if melhor else "Steam",
            "url": (melhor or {}).get("url"),
            "piso": ps.get(0, piso_marc), "piso_geral": piso_geral,
            "pisos": {"3m": ps.get(90), "6m": ps.get(180), "9m": ps.get(270), "1a": ps.get(365), "sempre": ps.get(0)},
            "tag": tag, "tag_texto": texto, "acima": acima,
            "raridade": an["nivel"], "raridade_texto": an["texto"], "no_piso": an["no_piso"], "selo": an["selo"],
            "selo_motivo": an["selo_motivo"], "piso_tipo": an["piso_tipo"], "piso_ref": an["piso_ref"], "rar_info": _rar_info(an),
            "score": an["score"],
            "keyshop": g.get("keyshop"), "hist_keyshop": g.get("hist_keyshop"), "gg_url": g.get("url"),
            "vale": a in vale, "novo": a in novos, "motivo": (vale.get(a) or {}).get("motivo"),
            "base_tenho": bool(j.get("tipo") == "dlc" and j.get("pai") in ctx.possuidos),
            "bundles": nb.get(a, 0), "n_dlcs": len(ctx.dlcs.get(a, [])), "modo": modo,
            "extra": a in extras, "fim": fim, "prioridade": j.get("prioridade"), "mudo": a in mudos,
            "favorito": analise.favorito(j, cfg["alerta"]),
        })
    b.con.close()
    return {"itens": out, "lojas": cfg["lojas"]}


def _rar_info(an):
    """O 'por que essa raridade' da ficha."""
    return {k: an.get(k) for k in ("corte_max", "eps_nivel", "por_ano", "ultima", "meses", "curto", "inicio")}


def _estado_dlcs(b, a, j):
    """Por que a ficha nao tem DLCs: falhou, a Steam nao informou ou ainda nao consultada (com a fila, se rodando)."""
    if j.get("tipo") != "jogo":
        return None
    ok, falha = b.ultima_consulta("dlcs", a), b.ultima_consulta("dlcs_falha", a)
    if falha and (not ok or falha > ok):
        return {"motivo": "falhou", "quando": falha}
    if ok:
        return {"motivo": "sem_dlcs", "quando": ok}
    p = __import__("radar.progresso", fromlist=["x"]).foto()
    rodando = p["ativo"] and (p["etapa"] or "").startswith("Steam: procurando DLCs") and p["total"]
    return {"motivo": "pendente", "fila": {"atual": p["atual"], "total": p["total"]} if rodando else None}


def api_jogo(q):
    a = int(q["appid"][0])
    cfg = config.carregar()
    b = Banco()
    ctx = analise.Contexto(b, cfg)
    j = ctx.jogos.get(a) or {}
    hist = {}
    for r in b.q("SELECT loja, preco, quando FROM preco WHERE appid=? ORDER BY quando", a):
        hist.setdefault(r["loja"], []).append([r["quando"], r["preco"]])
    atuais = {o["loja"]: o for o in b.ofertas_atuais([a]).get(a, [])}
    mins = {r["loja"]: r["m"] for r in _minimos(b, [a])}
    nomes = [l for l in set(atuais) | set(mins) if l not in NAO_LOJA]
    lojas = [{"loja": l, "atual": (atuais.get(l) or {}).get("preco"), "cheio": (atuais.get(l) or {}).get("cheio"),
              "corte": (atuais.get(l) or {}).get("corte"), "url": (atuais.get(l) or {}).get("url"),
              "menor": mins.get(l), "marcada": l.lower() in _marcadas(cfg), "vende": l in atuais} for l in nomes]
    lojas.sort(key=lambda x: (not x["marcada"], not x["vende"], x["atual"] if x["atual"] is not None else 10**12))
    rel = set(ctx.relevantes(a))
    dl = [{"appid": d["appid"], "nome": (ctx.jogos.get(d["appid"]) or {}).get("nome"), "classe": d["classe"],
           "origem": d["origem"], "preco": ctx.preco(d["appid"]), "tenho": d["appid"] in ctx.possuidos,
           "conta": d["appid"] in rel} for d in ctx.dlcs.get(a, [])]
    dl.sort(key=lambda d: (d["classe"], -(d["preco"] or 0)))
    cam = ctx.caminhos(a) if ctx.dlcs.get(a) or ctx.opcoes_do.get(a) else []
    for c in cam:
        o = ctx.opcoes.get(c["id"])
        c["itens"] = [{"appid": i, "nome": (ctx.jogos.get(i) or {}).get("nome") or str(i),
                       "tenho": i in ctx.possuidos, "lista": i in ctx.lista} for i in (o["itens"] if o else [])]
    combo = ctx.melhor_combinacao(a) if ctx.dlcs.get(a) else None
    if combo:
        combo["avulsos"] = [{"nome": (ctx.jogos.get(x) or {}).get("nome") or str(x), "preco": p} for x, p in combo["avulsos"]]
    gg = b.um("SELECT * FROM gg WHERE appid=?", a)
    if ctx.precos_parciais(a):
        gg = None
    marc = _marcadas(cfg)
    lojas_m = [l for l in hist if l.lower() in marc] + (["Steam (direto)"] if "steam" in marc else [])
    ofs_m = [o for o in atuais.values() if o["loja"].lower() in marc]
    melhor = min(ofs_m, key=lambda o: o["preco"]) if ofs_m else None
    an = analise.analisar(b.linhas_lote(lojas_m, [a]).get(a, []) if lojas_m else [], melhor["preco"] if melhor else None,
                          melhor["corte"] if melhor else 0, cfg_alerta=cfg["alerta"])
    r = {"jogo":{k: j.get(k) for k in ("appid", "nome", "tipo", "capa", "rpos", "rcount", "rotulo", "lancamento",
                                         "preco_steam", "cheio_steam", "desconto_steam", "pai")},
         "historico": hist, "lojas": lojas, "dlcs": dl, "dlcs_estado": None if dl else _estado_dlcs(b, a, j),
         "caminhos": cam, "combo": combo,
         "raridade": an["nivel"], "raridade_texto": an["texto"], "selo": an["selo"], "selo_motivo": an["selo_motivo"], "no_piso": an["no_piso"],
         "piso_tipo": an["piso_tipo"], "piso_ref": an["piso_ref"], "rar_info": _rar_info(an), "score": an["score"],
         "gg":dict(gg) if gg else None, "modo": config.modo_do_jogo(cfg, a), "classes": dlcmod.CLASSES,
         "tenho": a in ctx.possuidos, "tenho_manual": bool(b.um("SELECT 1 FROM tenho_manual WHERE appid=?", a)),
         "mudo": bool(b.um("SELECT 1 FROM silenciado WHERE appid=?", a)),
         "na_lista": a in ctx.lista, "fila": (lambda r: r["acao"] if r else None)(b.um("SELECT acao FROM fila_lista WHERE appid=?", a)),
         "ponte_vista": b.meta("ponte_vista")}
    b.con.close()
    return r


def _ler_carrinho():
    try:
        with open(caminhos.ARQ_CARRINHO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        b = Banco()  # migra o carrinho da versao anterior, que ficava no banco
        v = b.meta("carrinho_sim") or []
        b.con.close()
        return v


def _gravar_carrinho(itens):
    caminhos.garantir()
    tmp = caminhos.ARQ_CARRINHO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(itens, f)
    os.replace(tmp, caminhos.ARQ_CARRINHO)


def api_carrinho(_q):
    """Carrinho simulado: jogos/DLCs (com a loja escolhida) e bundles da Steam (com o preco para voce)."""
    cfg = config.carregar()
    b = Banco()
    itens = _ler_carrinho()
    apps = [int(i["appid"]) for i in itens if i.get("appid")]
    bids = [int(i["bundle"]) for i in itens if i.get("bundle")]
    if not itens:
        r0 = {"itens": [], "bundles": [], "sugestoes": [], "steam": b.meta("carrinho") or [], "ponte_vista": b.meta("ponte_vista")}
        b.con.close()
        return r0
    ctx = analise.Contexto(b, cfg)
    marc = _marcadas(cfg)
    lojas_m = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")} if l.lower() in marc]
    if "steam" in marc:
        lojas_m.append("Steam (direto)")
    atuais = b.ofertas_atuais(apps) if apps else {}
    nome = lambda a: (ctx.jogos.get(a) or {}).get("nome") or str(a)
    cobertos = {}
    bl = []
    for bid in bids:
        o = ctx.opcoes.get("bundle:%d" % bid)
        if not o:
            bl.append({"bundle": bid, "nome": "Bundle %d" % bid, "preco": None, "itens": []})
            continue
        for a in o["itens"]:
            cobertos.setdefault(a, []).append(o["nome"])
        bl.append({"bundle": bid, "nome": o["nome"], "capa": o.get("capa"), "preco": ctx.preco_bundle_pra_voce(o),
                   "vitrine": o["final"], "desconto": o.get("desconto_bundle") or o.get("desconto") or 0,
                   "cheio": sum((ctx.jogos.get(a) or {}).get("cheio_steam") or 0 for a in o["itens"] if a not in ctx.possuidos),
                   "itens": [{"appid": a, "nome": nome(a), "tenho": a in ctx.possuidos, "no_carrinho": a in apps} for a in o["itens"]]})
    out = []
    for it in itens:
        if not it.get("appid"):
            continue
        a = int(it["appid"])
        j = ctx.jogos.get(a) or {}
        ofs = sorted([o for o in atuais.get(a, []) if o["loja"].lower() in marc], key=lambda o: o["preco"])
        ps = b.pisos(a, lojas_m) if lojas_m else {}
        escolhida = next((o for o in ofs if o["loja"] == it.get("loja")), ofs[0] if ofs else None)
        tag, texto, acima = analise.etiqueta(escolhida["preco"], escolhida.get("cheio"), ps, cfg["alerta"]) \
            if escolhida and escolhida.get("corte") else (None, None, None)
        an = analise.analisar(b.linhas_lote(lojas_m, [a]).get(a, []), escolhida["preco"], escolhida.get("corte"),
                              cfg_alerta=cfg["alerta"]) if escolhida and escolhida.get("corte") and lojas_m else {}
        out.append({"appid": a, "nome": j.get("nome") or str(a), "capa": j.get("capa"), "tipo": j.get("tipo"),
                    "possuido": a in ctx.possuidos, "lojas": [{k: o.get(k) for k in ("loja", "preco", "cheio", "corte", "url")} for o in ofs],
                    "loja": escolhida["loja"] if escolhida else None, "piso": ps.get(0), "fim": _fim(escolhida, j),
                    "tag": tag, "tag_texto": texto, "acima": acima, "em_bundle": cobertos.get(a, []),
                    "raridade": an.get("nivel"), "raridade_texto": an.get("texto"), "selo": an.get("selo", False), "selo_motivo": an.get("selo_motivo"),
                    "piso_tipo": an.get("piso_tipo"), "piso_ref": an.get("piso_ref"),
                    "rpos": j.get("rpos") or 0, "rcount": j.get("rcount") or 0})
    # sugestoes: bundles da Steam com pelo menos 1 item do carrinho
    preco_esc = {x["appid"]: next((l["preco"] for l in x["lojas"] if l["loja"] == x["loja"]), None) for x in out}
    sug = []
    for oid, o in ctx.opcoes.items():
        if o["tipo"] != "bundle" or o["final"] is None or int(oid.split(":")[1]) in bids:
            continue
        comuns = [a for a in o["itens"] if a in preco_esc]
        if not comuns:
            continue
        separado = sum(preco_esc[a] or 0 for a in comuns)
        seu = ctx.preco_bundle_pra_voce(o)
        extras = [a for a in o["itens"] if a not in preco_esc and a not in ctx.possuidos]
        sug.append({"bundle": int(oid.split(":")[1]), "nome": o["nome"], "preco": seu, "separado": separado,
                    "diferenca": seu - separado, "comuns": [nome(a) for a in comuns], "comuns_ids": comuns,
                    "extras": [nome(a) for a in extras],
                    "extras_valor": sum((ctx.jogos.get(a) or {}).get("cheio_steam") or 0 for a in extras)})
    sug.sort(key=lambda x: (x["diferenca"] > 0, x["diferenca"], -len(x["comuns"])))
    ult = b.meta("ponte_ultimo_envio") or {}
    sem_pacote = [x["nome"] for x in out if (not x["loja"] or x["loja"] == "Steam") and not (ctx.jogos.get(x["appid"]) or {}).get("pacote")]
    r = {"itens": out, "bundles": bl, "sugestoes": sug[:10], "steam": b.meta("carrinho") or [], "ponte_vista": b.meta("ponte_vista"),
         "ponte_falhas": ult.get("itens_falhos") or [], "sem_pacote": sem_pacote}
    b.con.close()
    return r


def post_carrinho(d):
    """O carrinho fica num arquivo proprio: gravar nele nunca espera a coleta liberar o banco."""
    vistos, limpo = set(), []
    for i in (d.get("itens") or []):
        if i.get("bundle"):
            k, item = ("b", int(i["bundle"])), {"bundle": int(i["bundle"])}
        elif i.get("appid"):
            k, item = ("a", int(i["appid"])), {"appid": int(i["appid"]), "loja": i.get("loja")}
        else:
            continue
        if k not in vistos:
            vistos.add(k)
            limpo.append(item)
    _gravar_carrinho(limpo)
    return {"ok": True, "n": len(limpo)}


def api_buscar(q):
    """Nome, appid ou link da Steam -> resultados da loja."""
    termo = (q.get("q") or [""])[0].strip()
    cfg = config.carregar()
    if not termo:
        return {"itens": []}
    m = re.search(r"(?:app/)?(\d{2,8})\b", termo)
    if m and (termo.isdigit() or "store.steampowered.com" in termo):
        ids = [int(m.group(1))]
        res = [steam.normalizar_app(i) for i in steam.get_items([{"appid": a} for a in ids], cfg["pais"])]
        itens = [{"appid": j["appid"], "nome": j["nome"], "capa": j["capa"], "preco": j["preco_steam"],
                  "corte": j["desconto_steam"], "tipo": j["tipo"]} for j in res]
    else:
        r = http_json("https://store.steampowered.com/api/storesearch/?" + _up.urlencode(
            {"term": termo, "l": "brazilian", "cc": cfg["pais"]})) or {}
        itens = []
        for i in (r.get("items") or [])[:12]:
            pr = i.get("price") or {}
            fin, ini = pr.get("final"), pr.get("initial")
            itens.append({"appid": i.get("id"), "nome": i.get("name"), "capa": i.get("tiny_image"),
                          "preco": fin, "corte": round(100 * (1 - fin / ini)) if fin and ini else 0, "tipo": i.get("type")})
    b = Banco()
    lista = {r["appid"] for r in b.q("SELECT appid FROM jogo WHERE na_lista=1")}
    tem = {r["appid"] for r in b.q("SELECT appid FROM jogo WHERE possuido=1")}
    b.con.close()
    for i in itens:
        i["na_lista"], i["possuido"] = i["appid"] in lista, i["appid"] in tem
    return {"itens": itens}


def post_extra(d):
    """Passa a monitorar um jogo fora da lista de desejos (ou para de monitorar)."""
    a = int(d["appid"])
    cfg = config.carregar()
    ex = [int(x) for x in (cfg.get("extras") or [])]
    if d.get("remover"):
        ex = [x for x in ex if x != a]
    elif a not in ex:
        ex.append(a)
        b = Banco()  # ja traz nome, capa e preco da Steam agora; as outras lojas vem na proxima checagem
        for j in (steam.normalizar_app(i) for i in steam.get_items([{"appid": a}], cfg["pais"])):
            b.salvar_jogo(j)
            b.con.execute("UPDATE jogo SET na_lista=1 WHERE appid=?", (a,))
            b.registrar_preco(a, "Steam (direto)", j["preco_steam"], j["cheio_steam"], j["desconto_steam"], "steam")
        b.commit()
        b.con.close()
        if CONTROLE["servico"]:
            CONTROLE["servico"].agora()
    cfg["extras"] = ex
    config.salvar(cfg)
    return {"ok": True, "extras": ex}


def api_biblioteca(_q):
    """Visao de colecionador: valor da biblioteca, o que falta para completar cada jogo e as franquias."""
    cfg = config.carregar()
    b = Banco()
    ctx = analise.Contexto(b, cfg)
    J, tem = ctx.jogos, ctx.possuidos
    preco = lambda a: (J.get(a) or {}).get("preco_steam")
    cheio = lambda a: (J.get(a) or {}).get("cheio_steam") or preco(a)
    menor = lambda a: ((J.get(a) or {}).get("menor_itad") or None)
    consultados = {r["id"] for r in b.q("SELECT id FROM consulta_lenta WHERE tipo='dlcs'")}
    jogos, sem_lista = [], 0
    tot = {"hoje": 0, "cheio": 0, "menor": 0, "falta_hoje": 0, "falta_cheio": 0, "falta_menor": 0, "dlcs_tenho": 0, "dlcs_faltam": 0}
    dlc_tenho_total = sum(1 for a in tem if (J.get(a) or {}).get("tipo") == "dlc")
    for a in tem:
        j = J.get(a) or {}
        if j.get("tipo") != "jogo" or not j.get("nome"):
            continue
        dl = ctx.dlcs.get(a, [])
        rel = set(ctx.relevantes(a))
        tenho = [d["appid"] for d in dl if d["appid"] in tem]
        falta = [d for d in dl if d["appid"] in rel and d["appid"] not in tem and preco(d["appid"])]
        vl = [x for x in [a] + tenho if preco(x) is not None]
        v_hoje = sum(preco(x) for x in vl)
        v_cheio = sum(cheio(x) or 0 for x in vl)
        v_menor = sum((menor(x) if menor(x) is not None else preco(x)) for x in vl)
        f_hoje = sum(preco(d["appid"]) for d in falta)
        f_cheio = sum(cheio(d["appid"]) or 0 for d in falta)
        f_menor = sum((menor(d["appid"]) if menor(d["appid"]) is not None else preco(d["appid"])) for d in falta)
        for k, v in (("hoje", v_hoje), ("cheio", v_cheio), ("menor", v_menor), ("falta_hoje", f_hoje),
                     ("falta_cheio", f_cheio), ("falta_menor", f_menor)):
            tot[k] += v
        tot["dlcs_faltam"] += len(falta)
        if a not in consultados and not dl:
            sem_lista += 1
        rel_tem = len([d for d in tenho if d in rel])
        faltam_ids = {d["appid"] for d in falta}
        bunds = []
        if faltam_ids:
            for oid, o in ctx.opcoes.items():
                if o["tipo"] != "bundle" or o["final"] is None:
                    continue
                cobre = faltam_ids & set(o["itens"])
                if cobre:
                    seu = ctx.preco_bundle_pra_voce(o)
                    avulso = sum(preco(x) or 0 for x in cobre)
                    bunds.append({"bundle": int(oid.split(":")[1]), "nome": o["nome"], "preco": seu, "cobre": len(cobre),
                                  "avulso": avulso, "economia": avulso - seu})
            bunds.sort(key=lambda x: (-x["economia"], -x["cobre"]))
        jogos.append({
            "appid": a, "nome": j["nome"], "capa": j.get("capa"), "capa_v": j.get("capa_v"), "franquia": j.get("franquia"),
            "valor": v_hoje, "valor_cheio": v_cheio, "rpos": j.get("rpos") or 0, "rcount": j.get("rcount") or 0,
            "dlc_total": len(rel), "dlc_tenho": rel_tem, "dlc_tenho_todas": len(tenho),
            "falta_hoje": f_hoje, "falta_cheio": f_cheio, "falta_menor": f_menor, "bundles": bunds[:4],
            "falta": [{"appid": d["appid"], "nome": (J.get(d["appid"]) or {}).get("nome") or str(d["appid"]),
                       "preco": preco(d["appid"]), "cheio": cheio(d["appid"]),
                       "corte": (J.get(d["appid"]) or {}).get("desconto_steam") or 0,
                       "menor": menor(d["appid"]), "classe": d["classe"]} for d in falta],
        })
    tot["dlcs_tenho"] = dlc_tenho_total
    # series: agrupadas pelo nome (a "franquia" da Steam mistura coisas como "EA Play")
    from . import series
    itens = [dict(g, origem="tenho") for g in jogos]
    for a in ctx.lista:
        jj = J.get(a) or {}
        if jj.get("tipo") == "jogo" and jj.get("nome") and a not in tem:
            itens.append({"appid": a, "nome": jj["nome"], "capa": jj.get("capa"), "preco": jj.get("preco_steam"),
                          "cheio": jj.get("cheio_steam"), "corte": jj.get("desconto_steam") or 0, "origem": "lista"})
    franquias = []
    for k, membros in series.agrupar(itens).items():
        tenho_ = [m for m in membros if m["origem"] == "tenho"]
        lista_ = [m for m in membros if m["origem"] == "lista"]
        if not tenho_ or (len(tenho_) < 2 and not lista_):
            continue
        franquias.append({
            "nome": series.rotulo([m["nome"] for m in membros]),
            "tenho": [{"appid": m["appid"], "nome": m["nome"], "capa": m["capa"], "dlc_faltam": len(m["falta"]),
                       "falta_hoje": m["falta_hoje"], "valor_cheio": m["valor_cheio"]} for m in tenho_],
            "lista": [{"appid": m["appid"], "nome": m["nome"], "capa": m["capa"], "preco": m["preco"],
                       "cheio": m["cheio"], "corte": m["corte"]} for m in lista_]})
    for f in franquias:
        f["custo_lista"] = sum(x["preco"] or 0 for x in f["lista"])
        f["dlc_faltam"] = sum(x["dlc_faltam"] for x in f["tenho"])
        f["falta_dlc_hoje"] = sum(x["falta_hoje"] for x in f["tenho"])
        f["valor_tenho"] = sum(x["valor_cheio"] for x in f["tenho"])
        f["valor_falta"] = sum((x["cheio"] or x["preco"] or 0) for x in f["lista"]) + \
            sum(x["falta_cheio"] for x in jogos if x["appid"] in {t["appid"] for t in f["tenho"]})
    franquias.sort(key=lambda f: (-len(f["tenho"]), f["nome"].lower()))
    r = {"jogos": jogos, "total": tot, "n_jogos": len(jogos), "sem_lista_dlc": sem_lista,
         "franquias": franquias,
         "sem_dados": sum(1 for a in tem if (J.get(a) or {}).get("nome") is None),
         "falta_ids": [d["appid"] for g in jogos for d in g["falta"]],
         "atualizado": b.meta("ult_biblioteca")}
    b.con.close()
    return r


def api_acesso(_q):
    rl = rede_local()
    ips = ips_locais()
    t = token()
    return {"rede_local": rl, "porta": PORTA, "ips": ips, "pin": t if rl else None,
            "links": [_base(ip) + CAMINHO for ip in ips] if rl else []}


def post_acesso(d):
    cfg = config.carregar()
    cfg.setdefault("painel", {})
    if "rede_local" in d:
        cfg["painel"]["rede_local"] = bool(d["rede_local"])
        config.salvar(cfg)
    if d.get("novo_codigo"):
        token(novo=True)  # os aparelhos ja liberados precisam abrir o link novo
    if "rede_local" in d:
        threading.Thread(target=reiniciar, daemon=True).start()
    return {"ok": True}


def post_tenho(d):
    """Marca/desmarca "ja tenho" (para compras feitas depois do userdata.json)."""
    a = int(d["appid"])
    b = Banco()
    if d.get("tenho", True):
        b.con.execute("INSERT OR REPLACE INTO tenho_manual VALUES(?,?)", (a, datetime.now(timezone.utc).isoformat()))
        b.con.execute("UPDATE jogo SET possuido=1 WHERE appid=?", (a,))
    else:
        b.con.execute("DELETE FROM tenho_manual WHERE appid=?", (a,))
        b.con.execute("UPDATE jogo SET possuido=0 WHERE appid=?", (a,))
    b.commit()
    b.con.close()
    if d.get("tenho", True):
        _gravar_carrinho([i for i in _ler_carrinho() if i.get("appid") != a])
    return {"ok": True}


def post_silenciar(d):
    a = int(d["appid"])
    b = Banco()
    if d.get("mudo", True):
        b.con.execute("INSERT OR REPLACE INTO silenciado VALUES(?,?)", (a, datetime.now(timezone.utc).isoformat()))
    else:
        b.con.execute("DELETE FROM silenciado WHERE appid=?", (a,))
    b.commit()
    b.con.close()
    return {"ok": True}


def post_atualizar_tudo(_d):
    s = CONTROLE["servico"]
    if not s:
        return {"ok": False, "erro": "So funciona com o Radar aberto na bandeja."}
    s.agora(completo=True)
    return {"ok": True}


def api_ponte(_q):
    """Para a ponte (Tampermonkey) nas paginas da Steam: o que mandar para o carrinho e a fila da lista de desejos."""
    cfg = config.carregar()
    b = Banco()
    # quem ainda nao tem o pacote (subid) conhecido: pergunta a Steam agora, numa consulta so
    carr = _ler_carrinho()
    faltam = [int(i["appid"]) for i in carr if i.get("appid") and (i.get("loja") in (None, "", "Steam"))
              and not (b.um("SELECT pacote FROM jogo WHERE appid=?", int(i["appid"])) or {"pacote": None})["pacote"]]
    if faltam:
        try:
            for j in (steam.normalizar_app(x) for x in steam.get_items([{"appid": a} for a in faltam], cfg["pais"])):
                if j.get("pacote"):
                    b.con.execute("UPDATE jogo SET pacote=? WHERE appid=?", (j["pacote"], j["appid"]))
            b.commit()
        except Exception as e:
            _log_erro("/api/ponte (pacotes)", e)
    itens = []
    for it in carr:
        if it.get("bundle"):
            o = b.um("SELECT nome FROM opcao WHERE id=?", "bundle:%d" % int(it["bundle"]))
            itens.append({"tipo": "bundle", "bundleid": int(it["bundle"]), "nome": o["nome"] if o else str(it["bundle"]),
                          "url": "https://store.steampowered.com/bundle/%d/" % int(it["bundle"])})
        elif it.get("appid") and (it.get("loja") in (None, "", "Steam")):
            j = b.um("SELECT nome, pacote, possuido FROM jogo WHERE appid=?", int(it["appid"]))
            if j and j["possuido"]:
                continue
            itens.append({"tipo": "app", "appid": int(it["appid"]), "subid": j["pacote"] if j else None,
                          "nome": j["nome"] if j else str(it["appid"]),
                          "url": "https://store.steampowered.com/app/%d/" % int(it["appid"])})
    fila = [dict(r) for r in b.q("SELECT appid, acao FROM fila_lista ORDER BY quando")]
    b.con.close()
    return {"ok": True, "versao": VERSAO, "carrinho": itens, "fila": fila}


def post_ponte_feito(d):
    b = Banco()
    for f in d.get("lista") or []:
        if f.get("ok"):
            b.con.execute("DELETE FROM fila_lista WHERE appid=? AND acao=?", (int(f["appid"]), f.get("acao")))
            if f.get("acao") == "remove":
                b.con.execute("UPDATE jogo SET na_lista=0 WHERE appid=?", (int(f["appid"]),))
            else:
                b.con.execute("UPDATE jogo SET na_lista=1 WHERE appid=?", (int(f["appid"]),))
    c = d.get("carrinho")
    if c:
        b.meta("ponte_ultimo_envio", {"quando": datetime.now(timezone.utc).isoformat(), **c})
    b.meta("ponte_vista", datetime.now(timezone.utc).isoformat())
    b.commit()
    b.con.close()
    return {"ok": True}


def post_lista_steam(d):
    """Enfileira adicionar/tirar da lista de desejos da Steam (a ponte executa na proxima pagina da Steam)."""
    a, acao = int(d["appid"]), d.get("acao")
    b = Banco()
    if acao == "cancelar":
        b.con.execute("DELETE FROM fila_lista WHERE appid=?", (a,))
    elif acao in ("add", "remove"):
        b.con.execute("INSERT OR REPLACE INTO fila_lista VALUES(?,?,?)", (a, acao, datetime.now(timezone.utc).isoformat()))
        if acao == "add":  # passa a monitorar ja, sem esperar a Steam
            cfg = config.carregar()
            ex = [int(x) for x in (cfg.get("extras") or [])]
            if a not in ex:
                ex.append(a)
                cfg["extras"] = ex
                config.salvar(cfg)
    b.commit()
    b.con.close()
    return {"ok": True}


def post_atualizar_app(_d):
    from . import atualizador
    atualizador.abrir_janela_separada()
    return {"ok": True}


def post_sair(_d):
    s = CONTROLE.get("ao_sair")
    if not s:
        return {"ok": False, "erro": "o painel nao esta rodando pela bandeja"}
    threading.Timer(0.3, s).start()
    return {"ok": True}


def api_notificacoes(_q):
    b = Banco()
    rows = [dict(r) for r in b.q("""SELECT a.*, j.nome, j.capa FROM alerta a LEFT JOIN jogo j ON j.appid=a.appid
                                     ORDER BY a.quando DESC LIMIT 200""")]
    b.con.close()
    return {"itens": rows}


def api_alertas(_q):
    b = Banco()
    ult = b.meta("ultimos_alertas") or {}
    b.con.close()
    return ult


def api_config(_q):
    b = Banco()
    lojas = b.meta("lojas_itad") or []
    b.con.close()
    return {"config": config.carregar(), "lojas_itad": lojas, "classes": dlcmod.CLASSES}


# ------------------------------------------------------------------ escrita
def post_config(dados):
    cfg = config.carregar()
    novo = dados.get("config") or {}
    for k in ("lojas", "somente_drm_steam", "alerta", "keyshops", "dlc", "notificacoes", "intervalos_minutos", "completo", "extras",
              "verificacao_completa_dias"):
        if k in novo:
            cfg[k] = novo[k]
    config.salvar(cfg)
    return {"ok": True}


def post_dlc(d):
    if d.get("classe") not in dlcmod.CLASSES:
        return {"ok": False, "erro": "classe invalida"}
    b = Banco()
    b.con.execute("UPDATE dlc SET classe=?, origem='usuario' WHERE appid=?", (d["classe"], int(d["appid"])))
    b.commit()
    b.con.close()
    return {"ok": True}


def post_modo(d):
    cfg = config.carregar()
    jogos = cfg["completo"].setdefault("jogos", {})
    if d.get("modo") == "completo":
        jogos[str(int(d["appid"]))] = "completo"
    else:
        jogos.pop(str(int(d["appid"])), None)
    config.salvar(cfg)
    return {"ok": True}


def post_verificar(_d):
    s = CONTROLE["servico"]
    if not s:
        return {"ok": False, "erro": "O painel nao esta rodando pela bandeja."}
    s.agora()
    return {"ok": True}


def post_pausar(_d):
    b = Banco()
    b.meta("pausado", not b.meta("pausado"))
    v = b.meta("pausado")
    b.commit()
    b.con.close()
    return {"ok": True, "pausado": bool(v)}


GET = {"/api/resumo": api_resumo, "/api/lista": api_lista, "/api/jogo": api_jogo, "/api/alertas": api_alertas,
       "/api/notificacoes": api_notificacoes, "/api/config": api_config, "/api/carrinho": api_carrinho,
       "/api/buscar": api_buscar, "/api/biblioteca": api_biblioteca, "/api/acesso": api_acesso, "/api/ponte": api_ponte}
POST = {"/api/config": post_config, "/api/dlc": post_dlc, "/api/modo": post_modo,
        "/api/verificar": post_verificar, "/api/pausar": post_pausar, "/api/carrinho": post_carrinho,
        "/api/extra": post_extra, "/api/acesso": post_acesso, "/api/sair": post_sair, "/api/tenho": post_tenho,
        "/api/silenciar": post_silenciar, "/api/atualizar_tudo": post_atualizar_tudo,
        "/api/ponte/feito": post_ponte_feito, "/api/lista_steam": post_lista_steam, "/api/atualizar_app": post_atualizar_app}


def _log_erro(rota, e):
    import logging
    import traceback
    logging.getLogger("radar").error("Painel %s: %s\n%s", rota, e, traceback.format_exc())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _local(self):
        return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

    def _autorizado(self, u):
        """Do proprio PC: sempre. De outro aparelho: so depois de digitar o PIN (fica lembrado por 1 ano)."""
        if self._local():
            return True
        t = token()
        if ("kr=%s" % t) in (self.headers.get("Cookie") or ""):
            return True
        if u.path.startswith("/api/"):
            self._json({"erro": "nao autorizado"}, 401)
            return False
        self._pagina_pin()
        return False

    def _pagina_pin(self, erro=""):
        dados = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                 "<title>Kurokami Radar</title><body style='background:#1b2838;color:#c7d5e0;font:16px Arial;display:flex;"
                 "min-height:90vh;align-items:center;justify-content:center'><form method=post action='/entrar' "
                 "style='background:#171a21;padding:28px;max-width:320px;width:100%%;box-shadow:0 0 20px #000'>"
                 "<h2 style='color:#fff;margin:0 0 6px;letter-spacing:.06em'>KUROKAMI RADAR</h2>"
                 "<p style='color:#8f98a0;font-size:13px'>Digite o PIN que aparece no PC, em Configurações → Acesso pelo celular.</p>"
                 "<input name=pin inputmode=numeric autocomplete=one-time-code maxlength=6 autofocus "
                 "style='width:100%%;font-size:28px;letter-spacing:.4em;text-align:center;padding:10px;background:#0e141b;"
                 "border:0;color:#fff;box-sizing:border-box'>%s<button style='margin-top:12px;width:100%%;padding:12px;"
                 "border:0;background:linear-gradient(90deg,#75b022,#588a1b);color:#fff;font-size:15px'>Entrar</button>"
                 "</form>") % ("<p style='color:#ef6f6a;font-size:13px'>%s</p>" % erro if erro else "")
        dados = dados.encode("utf-8")
        self.send_response(401 if erro else 200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _entrar(self):
        import time
        ip = self.client_address[0]
        agora_ = time.time()
        TENTATIVAS[ip] = [x for x in TENTATIVAS.get(ip, []) if agora_ - x < 600]
        if len(TENTATIVAS[ip]) >= 8:
            return self._pagina_pin("Muitas tentativas. Espere 10 minutos.")
        n = int(self.headers.get("Content-Length") or 0)
        pin = parse_qs(self.rfile.read(n).decode("utf-8", "replace")).get("pin", [""])[0].strip()
        if pin != token():
            TENTATIVAS[ip].append(agora_)
            return self._pagina_pin("PIN errado.")
        self.send_response(303)
        self.send_header("Set-Cookie", "kr=%s; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly" % token())
        self.send_header("Location", CAMINHO)
        self.end_headers()

    def _json(self, obj, code=200):
        dados = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        u = urlparse(self.path)
        ok = self._autorizado(u)
        if not ok:
            return
        if u.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", CAMINHO)
            self.end_headers()
            return
        if u.path in (CAMINHO + "/ponte.user.js", "/ponte.user.js"):
            with open(os.path.join(os.path.dirname(HTML), "ponte.user.js"), "rb") as f:
                dados = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        if u.path == CAMINHO + "/acao":
            q = parse_qs(u.query)
            if not self._local() or not ("silenciar" in q or "atualizar" in q):
                return self._json({"erro": "acao invalida"}, 400)
            if "atualizar" in q:
                from . import atualizador
                atualizador.abrir_janela_separada()
                dados = ("<!doctype html><meta charset=utf-8><body style='background:#1b2838;color:#c7d5e0;font:15px Arial;padding:30px'>"
                         "<h3 style='color:#fff'>Abrindo a atualização do Kurokami Radar…</h3><p>Pode fechar esta aba.</p>").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)
                return
            post_silenciar({"appid": int(q["silenciar"][0])})
            dados = ("<!doctype html><meta charset=utf-8><body style='background:#1b2838;color:#c7d5e0;font:15px Arial;padding:30px'>"
                     "<h3 style='color:#fff'>Pronto: o Radar não avisa mais desse jogo.</h3>"
                     "<p>Para desfazer, abra o jogo no <a style='color:#66c0f4' href='%s'>painel</a>.</p>" % CAMINHO).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        if u.path in (CAMINHO, CAMINHO + "/"):
            with open(HTML, "rb") as f:
                dados = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        f = GET.get(u.path)
        if not f:
            return self._json({"erro": "o Radar aberto (versao %s) nao tem %s. Reinicie o Radar pela bandeja." % (VERSAO, u.path)}, 404)
        try:
            self._json(f(parse_qs(u.query)))
        except Exception as e:
            _log_erro(u.path, e)
            self._json({"erro": str(e)}, 500)

    def do_POST(self):
        if urlparse(self.path).path == "/entrar":
            return self._entrar()
        # so aceita chamadas do proprio painel (protege contra sites tentando mexer no seu config)
        origem = self.headers.get("Origin") or ""
        ponte = urlparse(self.path).path == "/api/ponte/feito" and self._local()
        if origem and origem != "http://%s" % (self.headers.get("Host") or "") and not ponte:
            return self._json({"erro": "origem recusada"}, 403)
        if not self._local():
            t = token()
            if ("kr=%s" % t) not in (self.headers.get("Cookie") or ""):
                return self._json({"erro": "nao autorizado"}, 401)
            if urlparse(self.path).path in ("/api/acesso", "/api/sair"):
                return self._json({"erro": "so pelo proprio PC"}, 403)
        f = POST.get(urlparse(self.path).path)
        if not f:
            return self._json({"erro": "o Radar aberto (versao %s) nao tem %s. Reinicie o Radar pela bandeja." % (VERSAO, self.path)}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n) or b"{}")
            self._json(f(d))
        except Exception as e:
            _log_erro(self.path, e)
            self._json({"erro": str(e)}, 500)


def iniciar(abrir=False):
    global PORTA
    host = "0.0.0.0" if rede_local() else "127.0.0.1"
    srv, erro = None, None
    for p in PORTAS:
        try:
            srv = ThreadingHTTPServer((host, p), Handler)
            PORTA = p
            break
        except OSError as e:
            erro = e
    if srv is None:
        raise erro
    srv.daemon_threads = True
    CONTROLE["srv"] = srv
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if abrir:
        webbrowser.open(url())
    return srv


def reiniciar():
    """Troca entre so-este-PC e rede local sem fechar o Radar."""
    import time
    antigo = CONTROLE.get("srv")
    if antigo:
        antigo.shutdown()
        antigo.server_close()
    time.sleep(0.5)
    iniciar()


def url():
    return _base("localhost") + CAMINHO
