"""Dados das páginas novas de Ofertas e Biblioteca (spec 09, amostra 8 de Ofertas e referência H2 da Biblioteca).
As páginas (ofertas.html e biblioteca.html) recebem tudo de uma vez, no mesmo formato compacto das amostras
(linhas em listas, capas da CDN encurtadas com "~"), e filtram e ordenam no navegador.
Montar custa alguns segundos (histórico de cada jogo): fica em cache até a próxima coleta ou mudança no painel."""
import json
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone

from . import analise, caminhos, config, series
from .banco import Banco
from .previsao import Previsor, eventos

CDN = 'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/'
VALIDADE = 600          # segundos; invalidar() vence antes
_CACHE = {}
_GER = [0]              # geração: invalidar() muda, e o que foi montado antes deixa de valer
_TRAVAS = {'ofertas': threading.Lock(), 'biblioteca': threading.Lock(), 'timer': threading.Lock()}


def invalidar():
    _GER[0] += 1


def _cache(nome, fazer):
    """Um cálculo por vez para cada página; quem chega no meio espera o mesmo resultado."""
    with _TRAVAS[nome]:
        c = _CACHE.get(nome)
        if c and c[2] == _GER[0] and time.time() - c[0] < VALIDADE:
            return c[1]
        g = _GER[0]
        r = fazer()
        _CACHE[nome] = (time.time(), r, g)
        return r


def curta(u):
    if not u:
        return ''
    u = u.split('?')[0]
    return '~' + u[len(CDN):] if u.startswith(CDN) else u


def _linhas_de(b, tabela, lojas, appids):
    por = defaultdict(list)
    ids = sorted(set(appids))
    for k in range(0, len(ids), 500):
        for r in b.q("SELECT appid, loja, preco, corte, quando FROM %s WHERE appid IN (%s) ORDER BY appid, quando"
                     % (tabela, ','.join(str(int(a)) for a in ids[k:k + 500]))):
            if r['loja'] in lojas:
                por[r['appid']].append({'loja': r['loja'], 'preco': r['preco'], 'corte': r['corte'], 'quando': r['quando']})
    return por


def _todas(q):
    """Todas as páginas de /api/promocoes com o pedido q (no próprio processo)."""
    from . import painel
    out, pg = [], 1
    while True:
        r = painel.api_promocoes({'q': [json.dumps(dict(q, pagina=pg, por_pagina=250))]})
        out += r['itens']
        if pg * 250 >= r['total']:
            return out, r
        pg += 1


def _linha(o, cv, fr, hist, prev, an=None):
    """Uma linha no formato da amostra (os índices são lidos pela função M() da página)."""
    if an:
        o = dict(o, **an)
    pr = o.get('piso_ref') or {}
    t = 'selo' if o.get('selo') else (o.get('tipo_oferta') or '')
    return [o['appid'], o['nome'], curta(cv.get(o['appid'])), curta(o.get('capa')), o.get('preco'), o.get('cheio'),
            o.get('corte') or 0, t, pr.get('preco'), (pr.get('quando_preco') or pr.get('quando') or '')[:7], o.get('volta_texto') or '',
            o.get('rpos') or 0, o.get('rcount') or 0, o.get('fim') or 0, o.get('lancamento') or 0,
            1 if o.get('em_breve') else 0, o.get('loja') or '', 1 if o.get('na_lista') else 0,
            1 if o.get('no_carrinho') else 0, None, fr.get(o['appid'], ''), 0,
            o.get('piso_geral'), (o.get('inicio') or '')[:10], o.get('selo_motivo') or '', o.get('volta_dica') or '',
            o.get('tipo') or 'jogo', 1 if o.get('tenho') else 0, 1 if hist else 0, prev]


def _montar_ofertas():
    agora_dt = datetime.now(timezone.utc)
    agora = agora_dt.timestamp()
    b = Banco()
    try:
        cv = {r[0]: r[1] for r in b.q("SELECT appid, capa_v FROM jogo WHERE capa_v IS NOT NULL AND capa_v<>''")}
        lista_db = [{'appid': r[0], 'nome': r[1], 'franquia': r[2]} for r in b.q("SELECT appid, nome, franquia FROM jogo WHERE na_lista=1")]
        fr = series.franquias(lista_db, {r[0]: r[1] for r in b.q('SELECT appid, nome FROM franquia_manual')})
        lojas = set((b.meta('promo_lojas') or {}).get('nomes') or []) or set(config.carregar().get('lojas') or [])
        lojas_l = lojas | ({'Steam (direto)'} if 'Steam' in lojas else set())
        com_hist = {r[0] for r in b.q('SELECT appid FROM promo_estado WHERE baixado IS NOT NULL')}

        ev = eventos(_linhas_de(b, 'preco', {'Steam'}, [x['appid'] for x in lista_db]).values(), agora)
        pv = Previsor(agora, ev)
        promo, resp = _todas({'fonte': 'steam', 'ordem': [['corte', 'desc'], ['nome', 'asc']]})
        lista, _ = _todas({'fonte': 'steam', 'relacao': {'na_lista': 'exigir'}, 'ordem': [['corte', 'desc'], ['nome', 'asc']]})

        H = {}
        lh = _linhas_de(b, 'preco', lojas_l, [o['appid'] for o in lista])
        L = []
        for o in lista:
            em = (o.get('corte') or 0) > 0 and o.get('preco') is not None
            lin = lh.get(o['appid'], [])
            t = ('selo' if o.get('selo') else o.get('tipo_oferta')) or 'nenhum'
            prev = pv.prever(lin, o.get('preco'), o.get('corte') or 0, t, em, o.get('fim')) if lin else None
            if lin:
                h = pv.hist(lin)
                if h:
                    H[o['appid']] = h
            L.append(_linha(o, cv, fr, bool(lin), prev))

        lid = {o['appid'] for o in lista}
        fora = [o for o in promo if o['appid'] not in lid]
        ph = _linhas_de(b, 'promo_hist', lojas, [o['appid'] for o in fora if o['appid'] in com_hist])
        P = []
        for o in promo:
            if o['appid'] in lid:
                P.append(o['appid'])          # o mesmo jogo da lista (a página usa a linha da lista)
                continue
            lin = ph.get(o['appid'])
            an = prev = None
            if lin and o.get('preco') is not None:
                x = analise.analisar(lin, o['preco'], o.get('corte') or 0, cfg_alerta={})
                tipos = analise.tipos_de(x)
                volta, _ = analise.costuma_voltar(x, o.get('corte') or 0)
                an = {'selo': x['selo'], 'selo_motivo': x['selo_motivo'], 'piso_ref': x['piso_ref'],
                      'tipo_oferta': analise.tipo_oferta(tipos), 'volta_texto': volta,
                      'volta_dica': analise.dica_volta(x, o.get('corte') or 0)}
                t = 'selo' if x['selo'] else (analise.tipo_oferta(tipos) or 'nenhum')
                prev = pv.prever(lin, o['preco'], o.get('corte') or 0, t, True, o.get('fim'))
                h = pv.hist(lin)
                if h:
                    H[o['appid']] = h
            P.append(_linha(o, cv, fr, bool(an), prev, an))

        # séries da biblioteca (pelo nome, como em series.py): "série que você tem" em Bons e baratos e no recorte
        lib = defaultdict(list)
        for r in b.q("SELECT nome FROM jogo WHERE possuido=1"):
            k = series.chave(r[0] or '')
            if k:
                lib[k].append(r[0])
        AF = {}
        for r in P + L:
            if isinstance(r, int) or r[27]:
                continue
            k = series.chave(r[1] or '')
            if k in lib:
                AF[r[0]] = series.rotulo(lib[k] + [r[1]])
        st = resp.get('steam') or {}
        return {'P': P, 'PT': resp['total'], 'L': L, 'steam': st.get('itens') or 0, 'quando': agora_dt.isoformat(),
                'EV': [int(t) for t in ev], 'H': H, 'AF': AF}
    finally:
        b.con.close()


def dados_ofertas():
    return _cache('ofertas', _montar_ofertas)


def _montar_biblioteca():
    from . import painel
    bd = painel.api_biblioteca({})
    b = Banco()
    try:
        ctx = analise.Contexto(b, config.carregar())
        J = ctx.jogos
        tempo = {r['appid']: (r['minutos'], r['ultima']) for r in b.q('SELECT appid, minutos, ultima FROM tempo_jogo')}
        conhecidos = [x for x in ctx.possuidos | ctx.lista if (J.get(x) or {}).get('tipo') == 'jogo' and J[x].get('nome')]
        itens = [{'appid': x, 'nome': J[x]['nome'], 'franquia': J[x].get('franquia')} for x in conhecidos]
        fr = series.franquias(itens, {r['appid']: r['nome'] for r in b.q('SELECT appid, nome FROM franquia_manual')})
        # o que falta: o preço de agora mais barato nas lojas marcadas, com a loja (o + põe no carrinho dessa loja)
        marc = painel._marcadas(config.carregar())
        atuais = b.ofertas_atuais([x for x in conhecidos if x not in ctx.possuidos])
        G = []
        for x in conhecidos:
            j = J[x]
            m, u = tempo.get(x, (None, None))
            o = None if x in ctx.possuidos else painel._melhor_oferta([o for o in atuais.get(x, []) if o['loja'].lower() in marc])
            pr = [o['preco'], o.get('cheio') or o['preco'], o.get('corte') or 0, o['loja']] if o else \
                [j.get('preco_steam'), j.get('cheio_steam'), j.get('desconto_steam') or 0, 'Steam']
            G.append([x, j['nome'], curta(j.get('capa_v')), fr[x], 1 if x in ctx.possuidos else 0, 1 if x in ctx.lista else 0,
                      j.get('lancamento') or 0, pr[0], pr[1], pr[2], m, u, j.get('rpos') or 0, curta(j.get('capa')), pr[3]])
        # jogos da lista que não são de nenhuma franquia que você tem não aparecem em lugar nenhum: ficam de fora
        minhas = {g[3].lower() for g in G if g[4]}
        G = [g for g in G if g[4] or g[3].lower() in minhas]
        C = [[g['appid'], g['dlc_tenho'], g['dlc_total'], g['valor_cheio'], g['falta_hoje'], g['falta_menor'],
              [[d['appid'], d['nome'], d['preco'], d['cheio'], d['corte'], d['menor'], d['classe']] for d in g['falta']]]
             for g in bd['jogos'] if g['falta'] or g['dlc_total']]
        # sem o retrato da conta (userdata.json, que a extensao grava), a biblioteca so tem jogos: as DLCs que voce tem ficam de fora
        return {'total': bd['total'], 'n': bd['n_jogos'], 'G': G, 'C': C, 'dlcs': bool(caminhos.achar_userdata(config.carregar()))}
    finally:
        b.con.close()


def dados_biblioteca():
    return _cache('biblioteca', _montar_biblioteca)


_TIMER = [None]


def aquecer(atraso=0):
    """Monta as duas em segundo plano (depois de uma coleta ou de um POST), para a página abrir na hora.
    Vários pedidos seguidos (ex.: + no carrinho) viram um só, `atraso` segundos depois do último."""
    def vai():
        for f in (dados_ofertas, dados_biblioteca):
            try:
                f()
            except Exception:
                pass   # a página tenta de novo ao abrir e mostra o erro
    with _TRAVAS['timer']:
        if _TIMER[0]:
            _TIMER[0].cancel()
        _TIMER[0] = threading.Timer(atraso, vai)
        _TIMER[0].daemon = True
        _TIMER[0].start()
