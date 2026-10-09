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

from . import VERSAO, analise, caminhos, config, conta_steam, dlc as dlcmod, ficha, steam
from .rede import http_json
from .banco import Banco

PORTAS = (80, 8787)       # tenta a 80 (link sem numero); se estiver ocupada, usa a 8787
PORTA = 8787              # a que ficou valendo
CAMINHO = "/kurokami"
ARQ_TOKEN = os.path.join(caminhos.DADOS, "painel_token.txt")
TENTATIVAS = {}           # ip -> [horarios], limita chutes de PIN
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel.html")
# páginas novas (spec 09) que o painel abre dentro das abas Ofertas e Biblioteca; os dados entram no lugar de /*DADOS*/{}
PAGINAS = {CAMINHO + "/ofertas": "ofertas.html", CAMINHO + "/biblioteca": "biblioteca.html"}
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


_PERFIL_PEDIDO = set()


def _perfil_info(b):
    """Nome e avatar do perfil Steam em uso (meta perfil_info). Se faltar ou for de outro SteamID, busca numa thread
    (uma vez por SteamID) e a proxima consulta ja traz."""
    sid = b.meta("steamid")
    info = b.meta("perfil_info") or {}
    if not sid or info.get("steamid") == sid:
        return info.get("avatar") and info or None
    if sid not in _PERFIL_PEDIDO:
        _PERFIL_PEDIDO.add(sid)

        def buscar():
            p = steam.perfil_publico(sid)
            if not p:   # rede fora: tenta de novo na proxima consulta
                _PERFIL_PEDIDO.discard(sid)
                return
            b2 = Banco()
            b2.meta("perfil_info", dict(p, steamid=sid))
            b2.commit()
            b2.con.close()
        threading.Thread(target=buscar, daemon=True).start()
    return None


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
         "completa_dias": config.carregar().get("verificacao_completa_dias", 7), "perfil": _perfil_info(b),
         "biblioteca_falhou": b.meta("biblioteca_falhou") or None}
    b.con.close()
    return r


# ------------------------------------------------------------------ linhas de Promocoes (cache em memoria)
# Uma linha por jogo da lista (+ monitorados), com tudo que a vitrine, a aba Promocoes e /api/lista mostram.
# Montar custa ~0,5 s (analisa o historico de todos); filtrar/ordenar no cache custa milissegundos. O cache e
# refeito quando termina uma coleta (servico), em qualquer POST do painel, quando o config muda e quando o
# userdata.json muda de data (conta_steam.assinatura); por seguranca, vence em 10 minutos.
_LINHAS = {"itens": None, "sig": None, "quando": 0, "ms": None}
_TRAVA_LINHAS = threading.Lock()
VALIDADE_LINHAS = 600


def invalidar_linhas():
    with _TRAVA_LINHAS:
        _LINHAS["itens"] = None
    from . import ofertas
    ofertas.invalidar()


def linhas_promocoes():
    """(linhas, cfg, conta) do cache, montando de novo se preciso."""
    import time
    cfg = config.carregar()
    sig = (conta_steam.assinatura(cfg), json.dumps(cfg, sort_keys=True, default=str))
    with _TRAVA_LINHAS:
        if _LINHAS["itens"] is not None and _LINHAS["sig"] == sig and time.time() - _LINHAS["quando"] < VALIDADE_LINHAS:
            return _LINHAS["itens"], cfg, _LINHAS["conta"]
        t0 = time.perf_counter()
        conta = conta_steam.relacao(cfg)
        itens = _montar_linhas(cfg, conta)
        _LINHAS.update(itens=itens, sig=sig, quando=time.time(), ms=round((time.perf_counter() - t0) * 1000),
                       conta={"tem_dados": conta["fonte"] is not None, "quando": conta["quando"]})
        return itens, cfg, _LINHAS["conta"]


def _montar_linhas(cfg, conta):
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
    carrinho = {int(i["appid"]) for i in _ler_carrinho() if i.get("appid")}
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
        tipos = analise.tipos_de(an)
        volta, volta_ordem = analise.costuma_voltar(an, corte)
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
            # spec 04 (0.15)
            "inicio": an["inicio"], "tipos": tipos, "tipo_oferta": analise.tipo_oferta(tipos),
            "volta_texto": volta, "volta_ordem": volta_ordem, "volta_dica": analise.dica_volta(an, corte),
            # toda linha daqui e da sua lista: desejos da Steam ou monitorado por voce ("extra" distingue os dois)
            "na_lista": True,
            "tenho": a in ctx.possuidos, "no_carrinho": a in carrinho, "em_bundle": nb.get(a, 0) > 0,
            "seguido": a in conta["seguidos"], "ignorado_steam": a in conta["ignorados"],
            "adulto": False,   # a lista e sua: +18 so se marca na Steam inteira
            "keyshop_barata": g.get("keyshop") is not None and preco is not None and g["keyshop"] < preco * 0.6,
        })
    b.con.close()
    return out


def api_lista(_q):
    itens, cfg, _conta = linhas_promocoes()
    return {"itens": itens, "lojas": cfg["lojas"]}


# ------------------------------------------------------------------ Steam inteira (spec 07)
# Quem esta em promocao na Steam e fora da lista vira uma LinhaSteam (leve, __slots__: ~50 MB com 108 mil).
# Os filtros leem o["campo"] como nas linhas da lista; campo que a linha leve nao tem vale None (fica fora do
# filtro que o exige). A relacao (tenho, carrinho, seguido, ignorado) vem de _STEAM["rel"], refeita junto com
# o cache da lista (qualquer POST, coleta, config).
class LinhaSteam:
    """Linha leve da Steam inteira: o["campo"] como nas linhas da lista; o que ela nao tem vale None (False na relacao)."""
    __slots__ = ("appid", "nome", "tipo", "capa", "rpos", "rcount", "rotulo", "lancamento", "preco", "cheio", "corte", "fim", "adulto",
                 # avaliacao (steam_promo.aval): a mesma da lista com historico; so a marca da ITAD sem ele
                 "tipos", "tipo_oferta", "selo", "selo_motivo", "piso_ref", "volta_texto", "volta_ordem", "volta_dica", "inicio")
    COLUNAS = __slots__[:13]

    def __getitem__(self, k):
        rel = _STEAM["rel"]
        if k in rel:
            return self.appid in rel[k]
        return getattr(self, k, None) if k in LinhaSteam.__slots__ else (False if k in RELACAO else None)

    def como_dict(self):
        d = {k: getattr(self, k) for k in LinhaSteam.__slots__}
        d.update({k: self[k] for k in RELACAO}, loja="Steam", steam_inteira=True, modo="base",
                 url="https://store.steampowered.com/app/%d/" % self.appid, pisos={}, em_bundle=False, bundles=0)
        return d


_STEAM = {"itens": [], "sig": None, "rel": {}, "rel_sig": None}
_TRAVA_STEAM = threading.Lock()


def _aplicar_aval(o, aval):
    """steam_promo.aval (JSON) -> campos da avaliacao da LinhaSteam."""
    av = json.loads(aval) if aval else {}
    o.tipos = av.get("tipos") or []
    o.tipo_oferta = analise.tipo_oferta(o.tipos)
    o.selo = "selo" in o.tipos
    for k in ("selo_motivo", "piso_ref", "volta_texto", "volta_ordem", "volta_dica", "inicio"):
        setattr(o, k, av.get(k))


def linhas_steam(itens_lista):
    """Linhas leves da Steam inteira (sem quem ja esta na lista) e quando foi a coleta. Refaz quando ha coleta nova."""
    b = Banco()
    try:
        quando = b.meta("ult_steam_inteira")
        sig = (quando, b.meta("promo_avaliado"))
        with _TRAVA_STEAM:
            if _STEAM["sig"] != sig:
                cols = LinhaSteam.COLUNAS
                novas = []
                for r in b.con.execute("SELECT %s, aval FROM steam_promo" % ", ".join(cols)):
                    o = LinhaSteam()
                    for k, v in zip(cols, r):
                        setattr(o, k, v)
                    _aplicar_aval(o, r[-1])
                    novas.append(o)
                _STEAM.update(itens=novas, sig=sig)
            if _STEAM["rel_sig"] is not itens_lista:   # o cache da lista foi refeito: relacao pode ter mudado
                conta = conta_steam.relacao(config.carregar())
                tenho = {r[0] for r in b.con.execute("SELECT appid FROM jogo WHERE possuido=1 UNION SELECT appid FROM tenho_manual")}
                _STEAM.update(rel={"tenho": tenho, "no_carrinho": {int(i["appid"]) for i in _ler_carrinho() if i.get("appid")},
                                   "seguido": conta["seguidos"], "ignorado_steam": conta["ignorados"]}, rel_sig=itens_lista)
            na_lista = {o["appid"] for o in itens_lista}
            return [o for o in _STEAM["itens"] if o.appid not in na_lista], quando
    finally:
        b.con.close()


# ------------------------------------------------------------------ /api/promocoes e /api/vitrine
class PedidoInvalido(Exception):
    """Vira HTTP 400 com a mensagem (em portugues)."""


RELACAO = ("na_lista", "extra", "no_carrinho", "seguido", "ignorado_steam", "mudo", "tenho", "base_tenho")
OUTROS = {"promo": lambda o: o["corte"] > 0, "bundle": lambda o: o["em_bundle"],
          "completo": lambda o: o["modo"] == "completo", "keyshop": lambda o: o["keyshop_barata"]}
TIPO_ITEM = ("jogo", "dlc")
POR_PAGINA = (50, 100, 250)
# campo de ordenacao -> valor (None = sem valor: sempre por ultimo)
ORDEM = {"nome": lambda o: (o["nome"] or "").lower(), "corte": lambda o: o["corte"] or None,
         "preco": lambda o: o["preco"], "volta": lambda o: o["volta_ordem"],
         "nota": lambda o: o["rpos"] if o["rcount"] else None, "analises": lambda o: o["rcount"] or None,
         "lancamento": lambda o: o["lancamento"], "fim": lambda o: o["fim"], "inicio": lambda o: o["inicio"]}
CAMPOS_Q = {"fonte", "busca", "relacao", "qualquer_um", "mostrar_so", "tipo", "outros", "preco_de", "preco_ate", "analises_de",
            "analises_ate", "nota_min", "desconto_min", "lanc_de", "lanc_ate", "em_breve", "ordem", "pagina", "por_pagina",
            "adulto"}
ADULTO = ("ocultar", "mostrar", "so")   # +18 da Steam inteira: oculto quando o campo nao vem


def _ler_q(qs):
    """Valida o q= de /api/promocoes. Campo ou valor desconhecido -> PedidoInvalido; ausente = sem filtro."""
    try:
        q = json.loads((qs.get("q") or ["{}"])[0] or "{}")
    except ValueError:
        raise PedidoInvalido("q não é um JSON válido")
    if not isinstance(q, dict):
        raise PedidoInvalido("q deve ser um objeto JSON")
    desconhecidos = set(q) - CAMPOS_Q
    if desconhecidos:
        raise PedidoInvalido("campo desconhecido: %s" % ", ".join(sorted(desconhecidos)))

    def lista(campo, validos):
        v = q.get(campo) or []
        if not isinstance(v, list) or any(x not in validos for x in v):
            raise PedidoInvalido("%s aceita só: %s" % (campo, ", ".join(validos)))
        return v

    def numero(campo):
        v = q.get(campo)
        if v in (None, ""):
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise PedidoInvalido("%s deve ser um número" % campo)
        return v

    def data(campo):
        v = q.get(campo)
        if v in (None, ""):
            return None
        try:
            return int(datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        except (TypeError, ValueError):
            raise PedidoInvalido("%s deve ser uma data aaaa-mm-dd" % campo)

    rel = q.get("relacao") or {}
    if not isinstance(rel, dict) or any(k not in RELACAO or v not in ("exigir", "excluir") for k, v in rel.items()):
        raise PedidoInvalido("relacao aceita {campo: \"exigir\"|\"excluir\"} com campo em: %s" % ", ".join(RELACAO))
    ordem = q.get("ordem") or [["corte", "desc"], ["nome", "asc"]]
    if not isinstance(ordem, list) or any(not isinstance(x, list) or len(x) != 2 or x[0] not in ORDEM
                                          or x[1] not in ("asc", "desc") for x in ordem):
        raise PedidoInvalido("ordem aceita [[campo, \"asc\"|\"desc\"], ...] com campo em: %s" % ", ".join(ORDEM))
    pp = q.get("por_pagina", 100)
    if pp not in POR_PAGINA:
        raise PedidoInvalido("por_pagina aceita só 50, 100 ou 250")
    pagina = q.get("pagina", 1)
    if isinstance(pagina, bool) or not isinstance(pagina, int) or pagina < 1:
        raise PedidoInvalido("pagina deve ser um inteiro a partir de 1")
    for campo in ("qualquer_um", "em_breve"):
        if campo in q and not isinstance(q[campo], bool):
            raise PedidoInvalido("%s deve ser true ou false" % campo)
    if q.get("fonte", "lista") not in ("lista", "steam"):
        raise PedidoInvalido("fonte aceita só lista ou steam")
    if q.get("adulto", "ocultar") not in ADULTO:
        raise PedidoInvalido("adulto aceita só: %s" % ", ".join(ADULTO))
    busca = q.get("busca") or ""
    if not isinstance(busca, str):
        raise PedidoInvalido("busca deve ser texto")
    return {"fonte": q.get("fonte", "lista"), "busca": busca.strip().lower(), "relacao": rel, "qualquer_um": bool(q.get("qualquer_um")),
            "mostrar_so": lista("mostrar_so", analise.TIPOS), "tipo": lista("tipo", TIPO_ITEM),
            "outros": lista("outros", list(OUTROS)),
            "faixas": [("preco", numero("preco_de"), numero("preco_ate")),
                       ("rcount", numero("analises_de"), numero("analises_ate")),
                       ("nota", numero("nota_min"), None), ("corte", numero("desconto_min"), None),
                       ("lancamento", data("lanc_de"), data("lanc_ate"))],
            "em_breve": bool(q.get("em_breve")), "adulto": q.get("adulto", "ocultar"), "ordem": ordem, "pagina": pagina, "por_pagina": pp}


def _filtros(f):
    """{grupo: predicado}; as contagens de um grupo usam todos os outros."""
    out = {}
    if f["busca"]:
        out["busca"] = lambda o: f["busca"] in (o["nome"] or "").lower()
    exigir = [k for k, v in f["relacao"].items() if v == "exigir"]
    excluir = [k for k, v in f["relacao"].items() if v == "excluir"]
    if exigir or excluir:
        junta = any if f["qualquer_um"] else all
        out["relacao"] = lambda o: (not exigir or junta(o[k] for k in exigir)) and not any(o[k] for k in excluir)
    if f["mostrar_so"]:
        out["mostrar_so"] = lambda o: o["tipo_oferta"] in f["mostrar_so"]
    if f["tipo"]:
        out["tipo"] = lambda o: o["tipo"] in f["tipo"]
    if f["outros"]:
        out["outros"] = lambda o: any(OUTROS[k](o) for k in f["outros"])
    for campo, de, ate in f["faixas"]:
        if de is None and ate is None:
            continue
        val = (lambda o: o["rpos"] if o["rcount"] else None) if campo == "nota" else (lambda o, c=campo: o[c])

        def faixa(o, val=val, de=de, ate=ate):
            v = val(o)  # sem valor com a faixa ligada: fica fora
            return v is not None and (de is None or v >= de) and (ate is None or v <= ate)
        out["faixa_" + campo] = faixa
    if f["em_breve"]:
        out["em_breve"] = lambda o: bool(o["em_breve"])
    if f["adulto"] != "mostrar":
        so = f["adulto"] == "so"
        out["adulto"] = lambda o: bool(o["adulto"]) == so
    return out


def _ordenar(itens, ordem):
    """Ordena pelos campos na ordem dada; sem valor sempre por ultimo; empate final pelo appid.
    Ordenacoes estaveis do ultimo criterio ao primeiro (com 100 mil linhas o cmp_to_key levava segundos)."""
    out = sorted(itens, key=lambda o: o["appid"])
    for campo, dir_ in reversed(ordem):
        f = ORDEM[campo]
        com, sem = [], []
        for o in out:
            (sem if f(o) is None else com).append(o)
        com.sort(key=f, reverse=dir_ == "desc")   # reverse mantem a estabilidade no Python
        out = com + sem
    return out


def api_promocoes(qs):
    """Explorador da aba Promocoes: filtra, conta e pagina no Hunter (pensando na Steam inteira, spec 07)."""
    f = _ler_q(qs)
    itens, cfg, conta = linhas_promocoes()
    steam_info = {"ligada": bool(cfg.get("steam_inteira", True)), "quando": None, "itens": 0}
    if f["fonte"] == "steam" and steam_info["ligada"]:
        leves, steam_info["quando"] = linhas_steam(itens)
        steam_info["itens"] = len(leves) + sum(1 for o in itens if o["corte"])
        itens = itens + leves
    filt = _filtros(f)
    passa = lambda o, sem=None: all(p(o) for g, p in filt.items() if g != sem)
    sel = [o for o in itens if passa(o)]
    contagens = {"mostrar_so": dict.fromkeys(analise.TIPOS, 0), "tipo": dict.fromkeys(TIPO_ITEM, 0)}
    for o in itens:
        if o["tipo_oferta"] in contagens["mostrar_so"] and passa(o, "mostrar_so"):
            contagens["mostrar_so"][o["tipo_oferta"]] += 1
        if o["tipo"] in contagens["tipo"] and passa(o, "tipo"):
            contagens["tipo"][o["tipo"]] += 1
    sel = _ordenar(sel, f["ordem"])
    pp, pg = f["por_pagina"], f["pagina"]
    pagina = [o if isinstance(o, dict) else o.como_dict() for o in sel[(pg - 1) * pp:pg * pp]]
    return {"total": len(sel), "pagina": pg, "por_pagina": pp, "itens": pagina,
            "contagens": contagens, "conta": conta, "steam": steam_info}


def api_vitrine(_q):
    """Prateleiras de Ofertas → Destaques (antiga "Vale a pena"): um bloco por tipo (exclusivo), so jogos (sem DLCs), sem os que voce tem. O Selo vale com
    qualquer corte (o selo_corte_minimo ja esta nele); os outros blocos so com corte >= desconto_minimo."""
    itens, cfg, _conta = linhas_promocoes()
    al = cfg["alerta"]
    dmin = al.get("desconto_minimo", 0) or 0
    lig = analise.tipos_ligados(al)
    out = {"avisa": {t: t in lig for t in analise.TIPOS}, "desconto_minimo": dmin}
    for t, n in (("selo", 10), ("novo", 8), ("igual", 8), ("24m", 8)):
        bl = [o for o in itens if o["tipo_oferta"] == t and o["tipo"] == "jogo" and not o["tenho"] and (t == "selo" or o["corte"] >= dmin)]
        bl.sort(key=lambda o: (-(o["corte"] or 0), o["preco"] if o["preco"] is not None else 10**12, o["appid"]))
        out[t] = {"total": len(bl), "itens": bl[:n]}
    out["na_lista"] = sum(1 for o in itens if o["na_lista"])
    return out


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
    if a not in ctx.lista and b.um("SELECT 1 FROM steam_promo WHERE appid=?", a):
        try:
            r = _jogo_steam(b, cfg, ctx, a)
            _ficha_local(b, ctx, cfg, a, r)
            return r
        finally:
            b.con.close()
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
    lin_m = b.linhas_lote(lojas_m, [a]).get(a, []) if lojas_m else []
    an = analise.analisar(lin_m, melhor["preco"] if melhor else None, melhor["corte"] if melhor else 0, cfg_alerta=cfg["alerta"])
    corte_m = melhor["corte"] if melhor else 0
    tipos = analise.tipos_de(an)
    volta, _ordem = analise.costuma_voltar(an, corte_m)
    # linha informativa: a Steam sozinha da Novo recorde/Selo e as lojas marcadas nao (decisao final da spec 04)
    st = atuais.get("Steam")
    regua = analise.regua_steam(lin_m, melhor["preco"] if melhor else None, corte_m,
                                b.linhas_lote(["Steam", "Steam (direto)"], [a]).get(a, []),
                                st["preco"] if st else None, st["corte"] if st else 0, cfg_alerta=cfg["alerta"])         if "steam" in marc else None
    r = {"jogo":{k: j.get(k) for k in ("appid", "nome", "tipo", "capa", "capa_v", "rpos", "rcount", "rotulo", "lancamento",
                                         "preco_steam", "cheio_steam", "desconto_steam", "pai")},
         "historico": hist, "lojas": lojas, "dlcs": dl, "dlcs_estado": None if dl else _estado_dlcs(b, a, j),
         "caminhos": cam, "combo": combo,
         "raridade": an["nivel"], "raridade_texto": an["texto"], "selo": an["selo"], "selo_motivo": an["selo_motivo"], "no_piso": an["no_piso"],
         "piso_tipo": an["piso_tipo"], "piso_ref": an["piso_ref"], "rar_info": _rar_info(an), "score": an["score"],
         "tipos": tipos, "tipo_oferta": analise.tipo_oferta(tipos), "volta_texto": volta,
         "volta_dica": analise.dica_volta(an, corte_m), "regua_steam": regua,
         "fim": _fim(melhor, j), "corte": corte_m,
         "gg":dict(gg) if gg else None, "modo": config.modo_do_jogo(cfg, a), "classes": dlcmod.CLASSES,
         "tenho": a in ctx.possuidos, "tenho_manual": bool(b.um("SELECT 1 FROM tenho_manual WHERE appid=?", a)),
         "mudo": bool(b.um("SELECT 1 FROM silenciado WHERE appid=?", a)),
         "na_lista": a in ctx.lista}
    try:
        _ficha_local(b, ctx, cfg, a, r)
    finally:
        b.con.close()
    return r


def _ficha_local(b, ctx, cfg, a, r):
    """O que a ficha nova (spec 09) le junto, sem rede: a fileira da franquia e o tempo jogado."""
    r["franquia"] = ficha.fileira(b, ctx, a, r["jogo"].get("nome"), _marcadas(cfg))
    r["jogado"] = ficha.jogado(b, a)


def api_jogo_extra(q):
    """O que a ficha busca na rede ao abrir (descricao e captura, HLTB e notas, conquistas), com cache: vem depois
    da ficha, para ela abrir na hora. Cada parte vem None se a fonte falhou."""
    a = int(q["appid"][0])
    b = Banco()
    try:
        tenho = bool(b.um("SELECT 1 FROM jogo WHERE appid=? AND possuido=1", a))
        return ficha.extras(b, config.carregar(), a, tenho, _log_erro)
    finally:
        b.con.close()


def post_franquia(d):
    """Troca a franquia do jogo a mao (juntar = escolher uma que existe; separar = nome novo); vazio volta ao automatico."""
    a, nome = int(d["appid"]), (d.get("nome") or "").strip()[:80]
    b = Banco()
    try:
        if nome:
            b.con.execute("INSERT OR REPLACE INTO franquia_manual VALUES(?,?,?)", (a, nome, datetime.now(timezone.utc).isoformat()))
        else:
            b.con.execute("DELETE FROM franquia_manual WHERE appid=?", (a,))
        b.commit()
    finally:
        b.con.close()
    return {"ok": True}


def _jogo_steam(b, cfg, ctx, a):
    """Ficha de um item da Steam inteira (fora da lista): o historico das lojas marcadas pela ITAD, baixado na hora
    se faltar (steam_inteira.historico_um), e a mesma avaliacao da lista. Das outras lojas so o menor (sem o preco
    de agora); sem DLCs, bundles e keyshop (isso vem ao monitorar o jogo)."""
    from . import credenciais, steam_inteira
    try:
        aviso = steam_inteira.historico_um(b, cfg, credenciais.ler("itad"), a, log=lambda *_: None)
    except Exception as e:   # ex.: banco ocupado pela coleta; a ficha abre com o historico que ja tem
        b.con.rollback()
        _log_erro("ficha da Steam inteira", e)
        aviso = "o histórico não pôde ser gravado agora (%s); tente de novo em alguns minutos" % e
    sp = dict(b.um("SELECT * FROM steam_promo WHERE appid=?", a))
    with _TRAVA_STEAM:   # a linha da tabela ja mostra o Selo/recorde novo, sem esperar a proxima coleta
        for o in _STEAM["itens"]:
            if o.appid == a:
                _aplicar_aval(o, sp.get("aval"))
                break
    nomes = set((b.meta("promo_lojas") or {}).get("nomes") or [])
    hist, linhas = {}, []
    for r in b.q("SELECT loja, preco, corte, quando FROM promo_hist WHERE appid=? ORDER BY quando", a):
        hist.setdefault(r["loja"], []).append([r["quando"], r["preco"]])
        if r["loja"] in nomes:
            linhas.append(dict(r))
    if "Steam" not in hist:
        hist["Steam"] = [[sp["visto"], sp["preco"]]]
    marc = _marcadas(cfg)
    lojas = []
    for l, pts in hist.items():
        vals = [p for _q, p in pts if p]
        lojas.append({"loja": l, "atual": None, "cheio": None, "corte": None, "url": None, "menor": min(vals) if vals else None,
                      "marcada": l.lower() in marc, "vende": False, "sem_atual": True})
    st = next(x for x in lojas if x["loja"] == "Steam")
    st.update(atual=sp["preco"], cheio=sp["cheio"], corte=sp["corte"], vende=True, sem_atual=False,
              url="https://store.steampowered.com/app/%d/" % a, menor=min(st["menor"] or sp["preco"], sp["preco"]))
    lojas.sort(key=lambda x: (not x["marcada"], not x["vende"], x["loja"]))
    try:
        an = analise.analisar(linhas, sp["preco"], sp["corte"], cfg_alerta=cfg["alerta"])
    except Exception as e:   # dado estranho no historico: ficha sem avaliacao, como no retrato (steam_inteira._aval)
        _log_erro("ficha da Steam inteira (avaliacao)", e)
        an = analise.analisar([], sp["preco"], sp["corte"], cfg_alerta=cfg["alerta"])
        aviso = aviso or "o histórico desta oferta veio com dados estranhos"
    tipos = analise.tipos_de(an)
    volta, _ordem = analise.costuma_voltar(an, sp["corte"])
    ps = Banco._pisos_de(linhas, (90, 180, 270, 365)) if linhas else {}
    tenho = a in ctx.possuidos or bool(b.um("SELECT 1 FROM tenho_manual WHERE appid=?", a))
    return {"jogo": {"appid": a, "nome": sp["nome"], "tipo": sp["tipo"], "capa": sp["capa"], "rpos": sp["rpos"],
                     "rcount": sp["rcount"], "rotulo": sp["rotulo"], "lancamento": sp["lancamento"], "preco_steam": sp["preco"],
                     "cheio_steam": sp["cheio"], "desconto_steam": sp["corte"], "pai": None},
            "historico": hist, "lojas": lojas, "dlcs": [], "dlcs_estado": None, "caminhos": [], "combo": None,
            "raridade": an["nivel"], "raridade_texto": an["texto"], "selo": an["selo"], "selo_motivo": an["selo_motivo"],
            "no_piso": an["no_piso"], "piso_tipo": an["piso_tipo"], "piso_ref": an["piso_ref"], "rar_info": _rar_info(an),
            "score": an["score"], "tipos": tipos, "tipo_oferta": analise.tipo_oferta(tipos), "volta_texto": volta,
            "volta_dica": analise.dica_volta(an, sp["corte"]), "regua_steam": None, "fim": sp["fim"], "corte": sp["corte"],
            "gg": None, "modo": "base", "classes": dlcmod.CLASSES, "tenho": tenho,
            "tenho_manual": bool(b.um("SELECT 1 FROM tenho_manual WHERE appid=?", a)),
            "mudo": bool(b.um("SELECT 1 FROM silenciado WHERE appid=?", a)), "na_lista": False,
            "steam_inteira": True, "aviso_hist": aviso, "adulto": bool(sp.get("adulto")),
            # o que a ficha da lista le da linha da tabela (IDX): melhor preco, pisos e marcas
            "item": {"appid": a, "preco": sp["preco"], "loja": "Steam", "corte": sp["corte"], "fim": sp["fim"],
                     "piso": ps.get(0), "piso_geral": None, "selo": an["selo"], "selo_motivo": an["selo_motivo"],
                     "tipo_oferta": analise.tipo_oferta(tipos), "piso_ref": an["piso_ref"], "piso_tipo": an["piso_tipo"],
                     "pisos": {"3m": ps.get(90), "6m": ps.get(180), "9m": ps.get(270), "1a": ps.get(365), "sempre": ps.get(0)}
                     if ps else None}}


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
    modos = {("b" if i.get("bundle") else "a", int(i.get("bundle") or i.get("appid") or 0)): _modo(i.get("modo")) for i in itens}
    apps = [int(i["appid"]) for i in itens if i.get("appid")]
    bids = [int(i["bundle"]) for i in itens if i.get("bundle")]
    if not itens:
        r0 = {"itens": [], "bundles": [], "sugestoes": [], "steam": b.meta("carrinho") or []}
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
            bl.append({"bundle": bid, "modo": modos[("b", bid)], "nome": "Bundle %d" % bid, "preco": None, "itens": []})
            continue
        for a in o["itens"]:
            cobertos.setdefault(a, []).append(o["nome"])
        bl.append({"bundle": bid, "modo": modos[("b", bid)], "nome": o["nome"], "capa": o.get("capa"), "preco": ctx.preco_bundle_pra_voce(o),
                   "vitrine": o["final"], "desconto": o.get("desconto_bundle") or o.get("desconto") or 0,
                   "cheio": sum((ctx.jogos.get(a) or {}).get("cheio_steam") or 0 for a in o["itens"] if a not in ctx.possuidos),
                   "itens": [{"appid": a, "nome": nome(a), "tenho": a in ctx.possuidos, "no_carrinho": a in apps} for a in o["itens"]]})
    out = []
    for it in itens:
        if not it.get("appid"):
            continue
        a = int(it["appid"])
        j = ctx.jogos.get(a) or {}
        ofs = [o for o in atuais.get(a, []) if o["loja"] == "Steam"]   # o carrinho so liga com a Steam
        ps = b.pisos(a, lojas_m) if lojas_m else {}
        escolhida = ofs[0] if ofs else None
        tag, texto, acima = analise.etiqueta(escolhida["preco"], escolhida.get("cheio"), ps, cfg["alerta"]) \
            if escolhida and escolhida.get("corte") else (None, None, None)
        an = analise.analisar(b.linhas_lote(lojas_m, [a]).get(a, []), escolhida["preco"], escolhida.get("corte"),
                              cfg_alerta=cfg["alerta"]) if escolhida and escolhida.get("corte") and lojas_m else {}
        out.append({"appid": a, "modo": modos[("a", a)], "nome": j.get("nome") or str(a), "capa": j.get("capa"), "tipo": j.get("tipo"),
                    "possuido": a in ctx.possuidos, "lojas": [{k: o.get(k) for k in ("loja", "preco", "cheio", "corte", "url")} for o in ofs],
                    "loja": escolhida["loja"] if escolhida else None, "piso": ps.get(0), "fim": _fim(escolhida, j),
                    "tag": tag, "tag_texto": texto, "acima": acima, "em_bundle": cobertos.get(a, []),
                    "raridade": an.get("nivel"), "raridade_texto": an.get("texto"), "selo": an.get("selo", False), "selo_motivo": an.get("selo_motivo"),
                    "piso_tipo": an.get("piso_tipo"), "piso_ref": an.get("piso_ref"),
                    "tipo_oferta": analise.tipo_oferta(analise.tipos_de(an)) if an else None, "corte": (escolhida or {}).get("corte") or 0,
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
    sem_pacote = [x["nome"] for x in out if not (ctx.jogos.get(x["appid"]) or {}).get("pacote")]
    r = {"itens": out, "bundles": bl, "sugestoes": sug[:10], "steam": b.meta("carrinho") or [], "sem_pacote": sem_pacote}
    b.con.close()
    return r


MODOS_CARRINHO = ("conta", "presente", "privado")


def _modo(m):
    """Como o item entra no carrinho da Steam: para a conta, de presente ou compra privada."""
    return m if m in MODOS_CARRINHO else "conta"


def post_carrinho(d):
    """O carrinho fica num arquivo proprio: gravar nele nunca espera a coleta liberar o banco."""
    vistos, limpo = set(), []
    for i in (d.get("itens") or []):
        if i.get("bundle"):
            k, item = ("b", int(i["bundle"])), {"bundle": int(i["bundle"]), "modo": _modo(i.get("modo"))}
        elif i.get("appid"):
            k, item = ("a", int(i["appid"])), {"appid": int(i["appid"]), "modo": _modo(i.get("modo"))}
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
         "atualizado": b.meta("ult_biblioteca"), "dlcs_promo": _dlcs_em_promocao(b, cfg, ctx, jogos)}
    b.con.close()
    return r


def _dlcs_em_promocao(b, cfg, ctx, jogos):
    """DLCs que contam (relevantes), que voce nao tem, de jogos que voce tem, com desconto agora (spec 04, D5).
    Preco: a oferta mais barata das lojas marcadas (ITAD) ou, se so houver ela, o preco da Steam ("preço Steam")."""
    marc = _marcadas(cfg)
    faltam = {d["appid"]: g for g in jogos for d in g["falta"]}
    if not faltam:
        return []
    atuais = b.ofertas_atuais(list(faltam))
    lojas_m = [l for l in {r["loja"] for r in b.q("SELECT DISTINCT loja FROM preco WHERE fonte LIKE 'itad%'")} if l.lower() in marc]
    if "steam" in marc:
        lojas_m.append("Steam (direto)")
    linhas = b.linhas_lote(lojas_m, list(faltam)) if lojas_m else {}
    out = []
    for a, g in faltam.items():
        j = ctx.jogos.get(a) or {}
        ofs = [o for o in atuais.get(a, []) if o["loja"].lower() in marc and o["preco"] is not None and o["corte"]]
        if not ofs:
            continue
        m = min(ofs, key=lambda o: o["preco"])
        an = analise.analisar(linhas.get(a, []), m["preco"], m["corte"], cfg_alerta=cfg["alerta"])
        tipos = analise.tipos_de(an)
        out.append({"appid": a, "nome": j.get("nome") or str(a), "capa": j.get("capa"), "pai": g["appid"], "pai_nome": g["nome"],
                    "preco": m["preco"], "cheio": m.get("cheio"), "corte": m["corte"], "loja": m["loja"],
                    "so_steam": m.get("fonte") == "catalogo", "fim": _fim(m, j), "tipo_oferta": analise.tipo_oferta(tipos),
                    "piso_ref": an["piso_ref"]})
    out.sort(key=lambda d: (-d["corte"], d["preco"]))
    return out


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
    invalidar_linhas()
    return {"ok": True}


def post_atualizar_tudo(_d):
    s = CONTROLE["servico"]
    if not s:
        return {"ok": False, "erro": "So funciona com o Hunter aberto na bandeja."}
    s.agora(completo=True)
    return {"ok": True}


def _itens_para_steam():
    """Itens da Steam do carrinho do Hunter (pacote ou bundle) para mandar ao carrinho da conta; descobre na hora o pacote que falta."""
    cfg = config.carregar()
    b = Banco()
    # quem ainda nao tem o pacote (subid) conhecido: pergunta a Steam agora, numa consulta so
    carr = _ler_carrinho()
    faltam = [int(i["appid"]) for i in carr if i.get("appid")
              and not (b.um("SELECT pacote FROM jogo WHERE appid=?", int(i["appid"])) or {"pacote": None})["pacote"]]
    if faltam:
        try:
            for j in (steam.normalizar_app(x) for x in steam.get_items([{"appid": a} for a in faltam], cfg["pais"])):
                if j.get("pacote"):
                    b.con.execute("UPDATE jogo SET pacote=? WHERE appid=?", (j["pacote"], j["appid"]))
            b.commit()
        except Exception as e:
            _log_erro("carrinho (pacotes)", e)
    itens = []
    for it in carr:
        if it.get("bundle"):
            o = b.um("SELECT nome FROM opcao WHERE id=?", "bundle:%d" % int(it["bundle"]))
            itens.append({"tipo": "bundle", "bundleid": int(it["bundle"]), "modo": _modo(it.get("modo")), "nome": o["nome"] if o else str(it["bundle"]),
                          "url": "https://store.steampowered.com/bundle/%d/" % int(it["bundle"])})
        elif it.get("appid"):
            j = b.um("SELECT nome, pacote, possuido FROM jogo WHERE appid=?", int(it["appid"]))
            if j and j["possuido"]:
                continue
            sp = dict(b.um("SELECT nome, pacote FROM steam_promo WHERE appid=?", int(it["appid"])) or {})   # Steam inteira (spec 07)
            itens.append({"tipo": "app", "appid": int(it["appid"]), "modo": _modo(it.get("modo")),
                          "subid": (j["pacote"] if j else None) or sp.get("pacote"),
                          "nome": j["nome"] if j else sp.get("nome") or str(it["appid"]),
                          "url": "https://store.steampowered.com/app/%d/" % int(it["appid"])})
    b.con.close()
    return itens


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


# ------------------------------------------------------------------ carrinho da Steam pela extensao do navegador
def post_steam_carrinho(_d):
    """Monta o endereco do carrinho da Steam com o pedido (#kurokami=PAIS:p<subid>[-modo],b<bundleid>[-modo]).
    Quem poe no carrinho e a extensao do Hunter (pasta extensao/), com a sessao da propria pagina da Steam:
    o Hunter nao ve token, cookie nem senha."""
    itens = _itens_para_steam()
    partes, sem = [], []
    for i in itens:
        m = "" if i["modo"] == "conta" else "-" + i["modo"]
        if i.get("tipo") == "bundle" and i.get("bundleid"):
            partes.append("b%d%s" % (i["bundleid"], m))
        elif i.get("subid"):
            partes.append("p%d%s" % (int(i["subid"]), m))
        else:
            sem.append(i.get("nome") or str(i.get("appid")))
    if not partes:
        return {"ok": False, "erro": "Nada para enviar: o carrinho não tem item da Steam com pacote conhecido.", "sem_pacote": sem}
    pais = str(config.carregar().get("pais") or "BR").upper()
    return {"ok": True, "n": len(partes), "sem_pacote": sem,
            "url": "https://store.steampowered.com/cart/#kurokami=%s:%s" % (pais, ",".join(dict.fromkeys(partes)))}


# ProgId do navegador padrao -> (nome, pagina de extensoes). Firefox e outros: sem suporte (extensao so Chromium).
NAVEGADORES = {"MSEdge": ("Edge", "edge://extensions"), "Chrome": ("Chrome", "chrome://extensions"),
               "Brave": ("Brave", "brave://extensions"), "Opera": ("Opera", "opera://extensions"),
               "Vivaldi": ("Vivaldi", "vivaldi://extensions")}


def _navegador_padrao():
    """(nome, exe, pagina de extensoes) do navegador padrao do Windows, ou None se nao for um que a extensao aceita."""
    import shlex
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice") as k:
            progid = winreg.QueryValueEx(k, "ProgId")[0]
        cmd = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, progid + r"\shell\open\command")
    except OSError:
        return None
    for prefixo, (nome, pagina) in NAVEGADORES.items():
        if progid.startswith(prefixo):   # ChromeHTML, ChromeBHTML (Beta), MSEdgeHTM, OperaGXStable, BraveHTML...
            exe = shlex.split(cmd, posix=False)[0].strip('"')
            return (nome, exe, pagina) if os.path.isfile(exe) else None
    return None


def post_steam_extensao(d):
    """Abre a pasta da extensao no Explorador e, com {navegador: true}, a pagina de extensoes do navegador padrao
    (o assistente do painel: o usuario liga o Modo do desenvolvedor e arrasta a pasta para a pagina)."""
    import subprocess
    if not os.path.isfile(os.path.join(caminhos.PASTA_EXTENSAO, "manifest.json")):
        return {"ok": False, "erro": "Pasta da extensão não encontrada: reinstale o Hunter."}
    r = {"ok": True, "pasta": caminhos.PASTA_EXTENSAO}
    if d.get("navegador"):
        nav = _navegador_padrao()
        if nav:
            subprocess.Popen([nav[1], nav[2]])
            r.update(navegador=nav[0], pagina=nav[2])
        else:
            r["aviso"] = "Seu navegador padrão não aceita a extensão. Abra o Chrome ou o Edge e digite chrome://extensions (ou edge://extensions)."
    os.startfile(caminhos.PASTA_EXTENSAO)
    return r


def post_steam_conta(d):
    """Dados da sua conta Steam que a extensao leu na loja, com a sessao da pagina (senha, token e cookie nunca chegam
    aqui): biblioteca com DLCs, lista de desejos, seguidos, ignorados e carrinho. So se o SteamID for o do perfil do
    Hunter: grava como userdata.json na pasta de dados (o formato do arquivo salvo a mao) e marca ja os possuidos."""
    sid = str(d.get("steamid") or "")
    b = Banco()
    try:
        meu = str(b.meta("steamid") or "")
        if not meu:
            return {"ok": False, "erro": "Configure o seu perfil Steam no Hunter antes."}
        if sid != meu:
            return {"ok": False, "erro": "A Steam aberta no navegador é de outra conta: o Hunter não usou os dados dela."}

        def ids(k):
            v = d.get(k) or []
            if not isinstance(v, list) or len(v) > 500000:
                raise ValueError("lista invalida: %s" % k)
            return sorted({x for x in v if type(x) is int and x > 0})
        if not ids("possuidos"):
            return {"ok": False, "erro": "A Steam devolveu a biblioteca vazia: o Hunter manteve a anterior."}
        u = {"rgOwnedApps": ids("possuidos"), "rgWishlist": ids("desejos"), "rgFollowedApps": ids("seguidos"),
             "rgIgnoredApps": ids("ignorados"), "rgAppsInCart": ids("carrinho"),
             "kurokami": {"fonte": "extensao", "steamid": sid, "quando": datetime.now(timezone.utc).isoformat(timespec="seconds")}}
        arq = os.path.join(caminhos.RAIZ_DADOS, "userdata.json")
        with open(arq + ".tmp", "w", encoding="utf-8") as f:
            json.dump(u, f)
        os.replace(arq + ".tmp", arq)
        # a coleta refaz a biblioteca inteira; ate la, o que voce tem ja sai das Promocoes
        for i in range(0, len(u["rgOwnedApps"]), 500):
            lote = u["rgOwnedApps"][i:i + 500]
            b.con.execute("UPDATE jogo SET possuido=1 WHERE appid IN (%s)" % ",".join("?" * len(lote)), lote)
        b.commit()
        return {"ok": True, "possuidos": len(u["rgOwnedApps"]), "seguidos": len(u["rgFollowedApps"]),
                "ignorados": len(u["rgIgnoredApps"])}
    finally:
        b.con.close()


def _limpar_sessao_qr():
    """O login por QR saiu na 0.16 (a Steam o tratava como celular novo). Quem tinha a sessao no cofre:
    revoga na Steam e apaga, uma vez. Falha de rede: tenta de novo na proxima abertura."""
    import logging
    import urllib.error
    from . import credenciais
    refresh = credenciais.ler("steam_refresh")
    if not refresh:
        return
    try:
        http_json("https://api.steampowered.com/IAuthenticationService/RevokeToken/v1/", tentativas=2,
                  form={"input_json": json.dumps({"token": refresh, "revoke_action": 1})})
    except urllib.error.HTTPError as e:
        if not 400 <= e.code < 500:   # 4xx: a Steam recusou (token vencido ou invalido): nao ha o que revogar; apaga
            logging.getLogger("radar").warning("Painel: nao revoguei a sessao QR antiga (HTTP %s); tento na proxima abertura", e.code)
            return
    except Exception as e:   # so o tipo do erro: nada que possa carregar o token
        logging.getLogger("radar").warning("Painel: nao revoguei a sessao QR antiga (%s); tento na proxima abertura", type(e).__name__)
        return
    credenciais.gravar("steam_refresh", "")


GET = {"/api/resumo": api_resumo, "/api/lista": api_lista, "/api/jogo": api_jogo, "/api/jogo_extra": api_jogo_extra, "/api/alertas": api_alertas,
       "/api/notificacoes": api_notificacoes, "/api/config": api_config, "/api/carrinho": api_carrinho,
       "/api/buscar": api_buscar, "/api/biblioteca": api_biblioteca, "/api/acesso": api_acesso,
       "/api/promocoes": api_promocoes, "/api/vitrine": api_vitrine}
POST = {"/api/config": post_config, "/api/dlc": post_dlc, "/api/modo": post_modo,
        "/api/verificar": post_verificar, "/api/pausar": post_pausar, "/api/carrinho": post_carrinho,
        "/api/extra": post_extra, "/api/acesso": post_acesso, "/api/sair": post_sair, "/api/tenho": post_tenho,
        "/api/silenciar": post_silenciar, "/api/atualizar_tudo": post_atualizar_tudo,
        "/api/atualizar_app": post_atualizar_app,
        "/api/steam/carrinho": post_steam_carrinho, "/api/steam/extensao": post_steam_extensao,
        "/api/steam/conta": post_steam_conta, "/api/franquia": post_franquia}


def _log_erro(rota, e):
    import logging
    import traceback
    logging.getLogger("radar").error("Painel %s: %s\n%s", rota, e, traceback.format_exc())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_local(self):
        """Host do cabecalho precisa ser o do proprio PC (barra DNS rebinding: um site com nome seu apontando para 127.0.0.1)."""
        h = (self.headers.get("Host") or "").lower()
        nome = h[:h.index("]") + 1] if h.startswith("[") and "]" in h else h.split(":")[0]
        return nome in ("localhost", "127.0.0.1", "[::1]")

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
                 "<title>Kurokami Hunter</title><body style='background:#050505;color:#d2d2d2;font:16px Arial;display:flex;"
                 "min-height:90vh;align-items:center;justify-content:center'><form method=post action='/entrar' "
                 "style='background:#000000;padding:28px;max-width:320px;width:100%%;box-shadow:0 0 20px #000'>"
                 "<h2 style='color:#fff;margin:0 0 6px;letter-spacing:.06em'>KUROKAMI HUNTER</h2>"
                 "<p style='color:#979797;font-size:13px'>Digite o PIN que aparece no PC, em Configurações → Acesso pelo celular.</p>"
                 "<input name=pin inputmode=numeric autocomplete=one-time-code maxlength=6 autofocus "
                 "style='width:100%%;font-size:28px;letter-spacing:.4em;text-align:center;padding:10px;background:#000000;"
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

    def _pagina_dados(self, arquivo):
        """Ofertas e Biblioteca: o modelo com os dados de agora dentro (gzip: ~3 MB viram ~400 KB no celular)."""
        from . import ofertas
        d = ofertas.dados_ofertas() if arquivo == "ofertas.html" else ofertas.dados_biblioteca()
        with open(os.path.join(os.path.dirname(HTML), arquivo), encoding="utf-8") as f:
            modelo = f.read()
        js = json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=str).replace("<", "\\u003c")   # nada no JSON fecha ou abre <script>/<!--
        dados = modelo.replace("/*DADOS*/{}", js, 1).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if "gzip" in (self.headers.get("Accept-Encoding") or ""):
            import gzip
            dados = gzip.compress(dados, 5)
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _json(self, obj, code=200):
        dados = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _steam_openid(self, u):
        """Entrar pela Steam (OpenID). So pelo proprio PC: outro aparelho nao pode trocar a conta do Hunter."""
        from . import steam_openid
        if not self._local() or not self._host_local():
            return self._json({"erro": "so pelo proprio PC"}, 403)
        base = _base("localhost")   # nunca montar a URL com o cabecalho Host
        if u.path.endswith("/entrar"):
            if self.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin"):   # nao deixa outro site disparar o login
                return self._json({"erro": "origem recusada"}, 403)
            destino = steam_openid.url_de_entrada(base)
        else:
            try:
                sid = steam_openid.concluir(parse_qs(u.query), base)
                cfg = config.carregar()
                cfg["perfil_steam"] = sid
                config.salvar(cfg)
                invalidar_linhas()
                destino = CAMINHO + "?steam=ok"
            except steam_openid.LoginInvalido as e:
                import html
                dados = ("<!doctype html><meta charset=utf-8><body style='background:#050505;color:#d2d2d2;font:15px Arial;padding:30px'>"
                         "<h3 style='color:#fff'>Não consegui entrar pela Steam</h3><p>%s</p>"
                         "<p><a style='color:#66c0f4' href='%s'>Voltar ao painel</a></p>" % (html.escape(str(e)), CAMINHO)).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(dados)
                return
        self.send_response(303)
        self.send_header("Location", destino)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

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
        if u.path == CAMINHO + "/acao":
            q = parse_qs(u.query)
            if not self._local() or not ("silenciar" in q or "atualizar" in q):
                return self._json({"erro": "acao invalida"}, 400)
            if "atualizar" in q:
                from . import atualizador
                atualizador.abrir_janela_separada()
                dados = ("<!doctype html><meta charset=utf-8><body style='background:#050505;color:#d2d2d2;font:15px Arial;padding:30px'>"
                         "<h3 style='color:#fff'>Abrindo a atualização do Kurokami Hunter…</h3><p>Pode fechar esta aba.</p>").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)
                return
            post_silenciar({"appid": int(q["silenciar"][0])})
            dados = ("<!doctype html><meta charset=utf-8><body style='background:#050505;color:#d2d2d2;font:15px Arial;padding:30px'>"
                     "<h3 style='color:#fff'>Pronto: o Hunter não avisa mais desse jogo.</h3>"
                     "<p>Para desfazer, abra o jogo no <a style='color:#66c0f4' href='%s'>painel</a>.</p>" % CAMINHO).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        if u.path in (CAMINHO + "/steam/entrar", CAMINHO + "/steam/retorno"):
            return self._steam_openid(u)
        if u.path in (CAMINHO, CAMINHO + "/"):
            with open(HTML, "rb") as f:
                dados = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        if u.path in PAGINAS:
            try:
                return self._pagina_dados(PAGINAS[u.path])
            except Exception as e:
                _log_erro(u.path, e)
                from html import escape
                dados = ("<!doctype html><meta charset=utf-8><body style='background:#050505;color:#d2d2d2;font:15px Arial;padding:40px'>"
                         "<h3 style='color:#fff;font-weight:400'>Não consegui montar esta página.</h3><p>%s</p>"
                         "<p><a style='color:#66c0f4' href='javascript:location.reload()'>Tentar de novo</a> · o erro foi para o radar.log.</p>"
                         % escape(str(e))).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)
                return
        f = GET.get(u.path)
        if not f:
            return self._json({"erro": "o Hunter aberto (versao %s) nao tem %s. Reinicie o Hunter pela bandeja." % (VERSAO, u.path)}, 404)
        try:
            self._json(f(parse_qs(u.query)))
        except PedidoInvalido as e:
            self._json({"erro": str(e)}, 400)
        except Exception as e:
            _log_erro(u.path, e)
            self._json({"erro": str(e)}, 500)

    def do_POST(self):
        if urlparse(self.path).path == "/entrar":
            return self._entrar()
        # so aceita chamadas do proprio painel (protege contra sites tentando mexer no seu config)
        origem = self.headers.get("Origin") or ""
        if origem and origem != "http://%s" % (self.headers.get("Host") or ""):
            return self._json({"erro": "origem recusada"}, 403)
        if not self._local():
            t = token()
            if ("kr=%s" % t) not in (self.headers.get("Cookie") or ""):
                return self._json({"erro": "nao autorizado"}, 401)
            if urlparse(self.path).path in ("/api/acesso", "/api/sair") or urlparse(self.path).path.startswith("/api/steam/"):
                return self._json({"erro": "so pelo proprio PC"}, 403)
        if urlparse(self.path).path.startswith("/api/steam/") and not (self._local() and self._host_local() and origem):
            return self._json({"erro": "so pelo proprio painel, neste PC"}, 403)
        f = POST.get(urlparse(self.path).path)
        if not f:
            return self._json({"erro": "o Hunter aberto (versao %s) nao tem %s. Reinicie o Hunter pela bandeja." % (VERSAO, self.path)}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n) or b"{}")
            r = f(d)
            invalidar_linhas()  # silenciar, extra, tenho, carrinho, modo, dlc, config... mudam as linhas de Promocoes
            from . import ofertas
            ofertas.aquecer(3)  # Ofertas e Biblioteca prontas de novo quando você voltar a elas
            self._json(r)
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
    threading.Thread(target=_limpar_sessao_qr, daemon=True).start()
    if abrir:
        webbrowser.open(url())
    return srv


def reiniciar():
    """Troca entre so-este-PC e rede local sem fechar o Hunter."""
    import time
    antigo = CONTROLE.get("srv")
    if antigo:
        antigo.shutdown()
        antigo.server_close()
    time.sleep(0.5)
    iniciar()


def url():
    return _base("localhost") + CAMINHO
