"""Orquestra a coleta: Steam (catalogo) -> ITAD (precos por loja + historico) -> GG.deals."""
import json
import os
import time
from datetime import datetime, timezone

from . import analise, caminhos, credenciais, dlc as dlcmod, ggdeals, itad, progresso, rede, steam, steam_inteira
from .banco import agora
from .config import modo_do_jogo


def _min_desde(banco, chave):
    t = banco.meta(chave)
    if not t:
        return 10**9
    return (datetime.now(timezone.utc) - datetime.fromisoformat(t)).total_seconds() / 60


def atualizar(cfg, banco, forcar=False, importar_hist=True, sem_limite=False, log=print, steam_agora=False):
    pais = cfg["pais"]
    k_steam, k_itad, k_gg = credenciais.ler("steam"), credenciais.ler("itad"), credenciais.ler("ggdeals")
    t0 = time.time()

    # ---------------------------------------------------------- 1. listas
    perfil = (cfg.get("perfil_steam") or "").strip()
    if not perfil:
        raise RuntimeError("Falta o seu perfil Steam: abra 'Chaves e perfil' no menu da bandeja.")
    sid = banco.meta("steamid")
    if not sid or banco.meta("steamid_perfil") != perfil:  # trocou de perfil: resolve de novo
        sid = steam.resolver_steamid(k_steam, perfil)
        banco.meta("steamid", sid)
        banco.meta("steamid_perfil", perfil)
    ud = {}
    arq = caminhos.achar_userdata(cfg)
    if arq:
        ud = steam.ler_userdata(arq)
    try:
        wl = steam.wishlist(k_steam, sid)
        fonte_wl = "Steam Web API"
    except Exception as e:
        wl, fonte_wl = ud.get("wishlist") or [], "userdata.json"
        log("   wishlist pela API falhou (%s); usando o userdata.json" % e)
    # userdata.json e um retrato (traz DLCs); a API traz os jogos de hoje. Juntamos os dois,
    # assim jogos comprados depois do retrato tambem contam.
    possuidos = set(ud.get("possuidos") or [])
    do_retrato = len(possuidos)
    falhou = None
    if k_steam:
        try:
            possuidos |= set(steam.biblioteca_api(k_steam, sid))
        except Exception as e:
            falhou = str(e)
            log("   biblioteca pela API falhou (%s)" % e)
        else:
            # tempo jogado e ultima vez, para a ficha; resposta vazia (perfil privado) nao apaga o que ja havia
            if steam.ULTIMO_TEMPO:
                try:
                    banco.salvar_tempo_jogo(steam.ULTIMO_TEMPO)
                except Exception as e:
                    log("   tempo jogado nao gravado (%s)" % e)
    mantida = bool(falhou and not do_retrato)
    if mantida:
        # sem a API e sem o retrato a biblioteca viria vazia e tudo que voce tem voltaria as Promocoes: fica a anterior
        # (marcar_listas grava o "ja tenho" do painel como possuido=1: tira aqui, ele volta la)
        manuais = {r["appid"] for r in banco.q("SELECT appid FROM tenho_manual")}
        possuidos = {r["appid"] for r in banco.q("SELECT appid FROM jogo WHERE possuido=1")} - manuais
        log("   mantida a biblioteca anterior (%d itens)" % len(possuidos))
    banco.meta("biblioteca_falhou", {"erro": falhou, "quando": agora(), "mantida": mantida} if falhou else {})
    if arq and do_retrato:
        idade = (time.time() - os.path.getmtime(arq)) / 86400
        log("   userdata.json de %d dia(s) atras: %d itens (DLCs incluidas)%s" % (
            idade, do_retrato, " + %d jogos novos pela API" % (len(possuidos) - do_retrato) if len(possuidos) > do_retrato else ""))
    elif not do_retrato:
        log("   sem userdata.json: biblioteca so com jogos (DLCs possuidas ficam de fora)")
    possuidos = sorted(possuidos)
    if not wl:
        raise RuntimeError("Lista de desejos vazia. Ela esta publica? Ou coloque o userdata.json na pasta.")
    extras = [int(a) for a in (cfg.get("extras") or []) if int(a) not in set(possuidos)]
    if extras:
        log("   + %d jogo(s) adicionados por voce no painel" % len([a for a in extras if a not in set(wl)]))
    wl = list(dict.fromkeys(list(wl) + extras))
    banco.marcar_listas(wl, possuidos, dict(steam.ULTIMA_PRIORIDADE))
    banco.meta("carrinho", ud.get("carrinho") or [])
    log("Lista de desejos: %d itens (%s) | biblioteca: %d itens" % (len(wl), fonte_wl, len(possuidos)))

    # ---------------------------------------------------------- 1b. Steam inteira (spec 07): logo no comeco (~10 s + ITAD em
    # lote), para nao esperar a coleta da lista; o historico de quem esta perto do recorde fica para o fim (etapa 6)
    banco.commit()   # nada de transacao aberta durante a rede (o painel tambem grava)
    steam_ligada = cfg.get("steam_inteira", True)
    if steam_ligada and (steam_agora or forcar or _min_desde(
            banco, "ult_steam_inteira") >= cfg["intervalos_minutos"].get("steam_inteira", 60)):
        try:
            steam_inteira.coletar(banco, cfg, log, k_itad)
        except Exception as e:   # nao derruba a coleta da lista; tenta de novo na proxima rodada
            log("   Steam inteira falhou (%s), tento na proxima" % rede.explicar(e))

    # ---------------------------------------------------------- 2. catalogo Steam (mais pesado, intervalo maior)
    if forcar or _min_desde(banco, "ult_steam") >= cfg["intervalos_minutos"]["steam"]:
        orc = None if sem_limite else cfg.get("chamadas_lentas_por_rodada", 120)
        pendente = catalogo_steam(cfg, banco, wl, possuidos, sid, k_steam, log, orc)
        if not pendente:  # se ficou consulta lenta para tras, a proxima rodada continua de onde parou
            banco.meta("ult_steam", agora())
        banco.commit()
    else:
        # jogo que entrou na lista agora (ou nunca teve os detalhes lidos) nao espera o intervalo do catalogo: sem isso
        # o aviso saia com o appid no lugar do nome e sem capa (Planet of Lana, 10/10). Sem resposta da Steam, tenta de novo em 1 dia.
        conhecidos = {r["appid"] for r in banco.q("SELECT appid FROM jogo WHERE nome IS NOT NULL")}
        novos = [a for a in wl if a not in conhecidos and not banco.consultado("nome", a, 1)]
        if novos:
            log("Steam: %d jogo(s) sem detalhes na lista, lendo agora..." % len(novos))
            catalogo_steam(cfg, banco, novos, possuidos, sid, k_steam, log, None if sem_limite else cfg.get("chamadas_lentas_por_rodada", 120))
            for a in novos:
                banco.marcar_consulta("nome", a)
            banco.commit()
        else:
            log("Catalogo Steam recente, pulando (use --tudo para forcar)")

    # ---------------------------------------------------------- 2b. biblioteca (1x por dia)
    if forcar or _min_desde(banco, "ult_biblioteca") >= 24 * 60:
        try:
            coletar_biblioteca(cfg, banco, possuidos, k_itad, log)
            banco.meta("ult_biblioteca", agora())
            banco.commit()
        except Exception as e:
            log("   biblioteca falhou (%s), tento na proxima" % e)

    # ---------------------------------------------------------- 3. ITAD
    ofertas = {}
    lojas_marcadas = set()
    if k_itad:
        try:
            ofertas, lojas_marcadas = coletar_itad(cfg, banco, wl, k_itad, importar_hist, log)
        except itad.ChaveRecusada as e:
            log("!! %s. Sigo so com Steam e GG.deals. Teste com: py radar.py testar" % e)
    else:
        log("Sem chave da ITAD: sem precos de outras lojas nem historico.")

    # ---------------------------------------------------------- 4. GG.deals (dados mudam de hora em hora)
    gg = {}
    if k_gg and (forcar or _min_desde(banco, "ult_gg") >= cfg["intervalos_minutos"]["ggdeals"]):
        log("GG.deals: consultando %d jogos..." % len(wl))
        try:
            gg = ggdeals.precos(k_gg, wl, pais.lower(), log)
            # A GG.deals pega a edicao mais barata, inclusive "partes" (HITMAN 3 aparece a R$ 8,09).
            # Nesses jogos o numero dela nao representa o jogo inteiro, entao nao entra no historico.
            parciais = {r["appid"] for r in banco.q(
                "SELECT DISTINCT jo.appid FROM jogo_opcao jo JOIN opcao o ON o.id=jo.opcao WHERE o.papel='parcial'")}
            for a in parciais & set(gg):
                gg[a]["parcial"] = True
            for a, g in gg.items():
                if g.get("parcial"):
                    banco.salvar_gg(a, g)
                    continue
                banco.salvar_gg(a, g)
                banco.registrar_preco(a, analise.LOJA_GG_OFICIAL, g["oficial"], None, None, "gg", g.get("url"))
                banco.registrar_preco(a, analise.LOJA_GG_KEYSHOP, g["keyshop"], None, None, "gg", g.get("url"))
            banco.meta("ult_gg", agora())
            log("   %d jogos com preco na GG.deals" % len(gg))
        except ggdeals.ChaveRecusada as e:
            log("!! %s. Confira com: py radar.py chaves" % e)
    if not gg:  # usa a ultima leitura guardada
        gg = {r["appid"]: dict(r) for r in banco.q("SELECT * FROM gg")}

    # ---------------------------------------------------------- 5. custo completo (vira historico proprio)
    ctx = analise.Contexto(banco, cfg)
    n = 0
    for a in ctx.lista:
        if ctx.dlcs.get(a):
            m = ctx.melhor_completo(a)
            if m and banco.registrar_preco(a, analise.LOJA_COMPLETO, m["custo_completo"], None, None, "calculado"):
                n += 1
    banco.commit()

    # ---------------------------------------------------------- 6. historico da Steam inteira (so quem esta perto do recorde, aos poucos)
    if steam_ligada and k_itad and banco.meta("ult_steam_inteira"):
        try:
            steam_inteira.historicos(banco, cfg, k_itad, log, cfg.get("steam_inteira_hist_por_rodada", 60))
        except Exception as e:
            log("   historico da Steam inteira falhou (%s), tento na proxima" % rede.explicar(e))
    log("Coleta concluida em %.0fs" % (time.time() - t0))
    return ofertas, gg, lojas_marcadas


def catalogo_steam(cfg, banco, wl, possuidos, sid, k_steam, log, orcamento=None):
    pais = cfg["pais"]
    log("Steam: detalhes de %d itens da lista..." % len(wl))
    itens = [steam.normalizar_app(i) for i in steam.get_items([{"appid": a} for a in wl], pais, log=log)]
    bundles_de = {}
    for j in itens:
        banco.salvar_jogo(j)
        for b in j["_bundles"]:
            bundles_de.setdefault(b, set()).add(j["appid"])
    banco.commit()
    log("   %d itens com dados" % len(itens))

    # ---- edicoes (pacotes): o conteudo real so vem pela loja, entao guardamos em cache
    pend = []
    manuais = set(banco.meta("edicoes_manuais") or [])
    for j in itens:
        for e in j["_edicoes"]:
            if e["papel"] == "base":
                continue
            oid = "edicao:%d" % e["packageid"]
            conhecido = banco.itens_opcao(oid)
            banco.salvar_opcao({"id": oid, "tipo": "edicao", "nome": e["nome"], "final": e["final"], "cheio": e["cheio"],
                                "desconto": e["desconto"], "itens": conhecido or [j["appid"]], "papel": e["papel"]})
            banco.ligar_opcao(j["appid"], oid)
            if oid in manuais:
                continue
            confirmado = conhecido and len(conhecido) > 1
            if e["papel"] != "parcial" and not banco.consultado("pacote", e["packageid"], 30 if confirmado else 1):
                pend.append((e["packageid"], oid))
    restante = orcamento
    sobrou = 0
    if pend:
        log("Steam: conteudo de %d edicoes..." % len(pend))
        for i in range(0, len(pend), 40):
            lote = pend[i:i + 40]
            cont = steam.conteudo_pacotes([pid for pid, _ in lote], pais, log)
            for pid, oid in lote:
                if cont.get(pid):
                    banco.con.execute("UPDATE opcao SET itens=? WHERE id=?", (json.dumps(cont[pid]), oid))
                banco.marcar_consulta("pacote", pid)
            banco.commit()
            progresso.passo(min(i + 40, len(pend)), len(pend))
            log("   %d/%d" % (min(i + 40, len(pend)), len(pend)))

    # ---- DLCs dos jogos da lista
    jogos = [j["appid"] for j in itens if j["tipo"] == "jogo"]
    log("Steam: procurando DLCs de %d jogos..." % len(jogos))
    mapa = {}
    if k_steam and not banco.meta("dlcforapps_bloqueado"):
        mapa = steam.dlcs_dos_jogos(k_steam, sid, jogos, pais, log)
        if mapa is None:
            banco.meta("dlcforapps_bloqueado", True)
            mapa = {}
    mapa = mapa or {}
    if not mapa:
        # depois da lista de desejos, os jogos que voce ja tem (para a aba Biblioteca)
        meus = [r["appid"] for r in banco.q("SELECT appid FROM jogo WHERE possuido=1 AND tipo='jogo'") if r["appid"] not in set(jogos)]
        faltam = [a for a in jogos if not banco.consultado("dlcs", a, 14)]
        faltam_meus = [a for a in meus if not banco.consultado("dlcs", a, 30)]
        # primeiro quem mais precisa: jogos no modo "completo", depois os que estao em promocao
        promo = {j["appid"] for j in itens if j["desconto_steam"]}
        faltam.sort(key=lambda a: (modo_do_jogo(cfg, a) != "completo", a not in promo))
        faltam += faltam_meus
        sobrou = 0
        if restante is not None and len(faltam) > restante:
            sobrou = len(faltam) - restante
            log("   %d jogos sem lista de DLCs; esta rodada consulta %d e as proximas continuam" % (len(faltam), restante))
            faltam = faltam[:restante]
        if faltam:
            log("   usando a loja (plano B): %d jogos, ~%d min" % (len(faltam), len(faltam) * 1.6 / 60 + 1))
        for i, a in enumerate(faltam, 1):
            progresso.passo(i, len(faltam))
            try:
                for d in steam.dlcs_pela_loja(a, pais):
                    mapa[d] = a
                banco.marcar_consulta("dlcs", a)
                banco.limpar_consulta("dlcs_falha", a)
            except Exception as e:
                # tipo separado: "dlcs_falha" nao conta como consultado, o jogo volta na proxima rodada
                banco.marcar_consulta("dlcs_falha", a)
                log("   DLCs de %s falharam (%s)" % (a, e))
            if i % 50 == 0:
                banco.commit()
                log("   %d/%d" % (i, len(faltam)))
        conhecidas = {r["appid"]: r["pai"] for r in banco.q("SELECT appid, pai FROM dlc")}
        for d, pai in conhecidas.items():
            mapa.setdefault(d, pai)
    if mapa:
        log("   %d DLCs, lendo precos..." % len(mapa))
        for d in (steam.normalizar_app(i) for i in steam.get_items([{"appid": a} for a in mapa], pais, log=log)):
            d["pai"] = d["pai"] or mapa.get(d["appid"])
            for b in d["_bundles"]:  # bundles de DLC (ex.: "Deluxe Pack DLC"), uteis para completar a biblioteca
                bundles_de.setdefault(b, set()).add(d["appid"])
            banco.salvar_jogo(d)
            banco.salvar_dlc(d["appid"], d["pai"], dlcmod.classificar(d["nome"]))
        banco.commit()

    # ---- bundles que contem jogos da lista
    log("Steam: lendo %d bundles..." % len(bundles_de))
    faltam_preco = set()
    conhecidos = {r["appid"] for r in banco.q("SELECT appid FROM jogo WHERE nome IS NOT NULL")}
    for it in steam.get_items([{"bundleid": b} for b in bundles_de], pais, {"include_included_items": True}, log=log):
        o = steam.normalizar_opcao(it, "bundle")
        if len(o["itens"]) < 2:
            continue
        banco.salvar_opcao(o)
        for a in bundles_de.get(int(o["id"].split(":")[1]), ()):
            banco.ligar_opcao(a, o["id"])
        faltam_preco |= set(o["itens"]) - conhecidos
    for r in banco.q("SELECT itens FROM opcao WHERE tipo='edicao'"):
        faltam_preco |= set(json.loads(r["itens"] or "[]")) - conhecidos
    if faltam_preco:
        log("   precos de %d itens que so aparecem em bundles e edicoes..." % len(faltam_preco))
        for d in (steam.normalizar_app(i) for i in steam.get_items([{"appid": a} for a in faltam_preco], pais, log=log)):
            banco.salvar_jogo(d)
    # A Steam diz de qual jogo cada DLC e (parent_appid). Toda DLC que apareceu em bundle ou edicao
    # entra na lista do jogo-pai na hora, sem esperar a busca lenta pela loja.
    novas = banco.q("SELECT j.appid, j.pai, j.nome FROM jogo j LEFT JOIN dlc d ON d.appid=j.appid "
                    "WHERE j.tipo='dlc' AND j.pai IS NOT NULL AND d.appid IS NULL")
    for r in novas:
        banco.salvar_dlc(r["appid"], r["pai"], dlcmod.classificar(r["nome"]))
    if novas:
        log("   %d DLCs reconhecidas pelos bundles e edicoes" % len(novas))
    # preco da propria Steam tambem vira historico (caso a ITAD nao tenha o item)
    for r in banco.q("SELECT appid, preco_steam, cheio_steam, desconto_steam FROM jogo WHERE na_lista=1"):
        banco.registrar_preco(r["appid"], "Steam (direto)", r["preco_steam"], r["cheio_steam"], r["desconto_steam"], "steam")
    return sobrou > 0


def coletar_biblioteca(cfg, banco, possuidos, k_itad, log):
    """Precos, franquias e menor historico de tudo que voce tem (jogos e DLCs)."""
    pais = cfg["pais"]
    log("Biblioteca: detalhes de %d itens que voce tem..." % len(possuidos))
    n = 0
    for d in (steam.normalizar_app(i) for i in steam.get_items([{"appid": a} for a in possuidos], pais, log=log)):
        banco.salvar_jogo(d)
        if d["tipo"] == "dlc" and d["pai"]:
            banco.salvar_dlc(d["appid"], d["pai"], dlcmod.classificar(d["nome"]))
        n += 1
    banco.commit()
    log("   %d itens lidos" % n)
    if not k_itad:
        return
    cache = _cache_itad(cfg, banco)
    # o que voce tem + as DLCs que faltam nos seus jogos (para o "menor historico" do que falta)
    faltam = [r["appid"] for r in banco.q("SELECT d.appid FROM dlc d JOIN jogo j ON j.appid=d.pai "
                                          "WHERE j.possuido=1 AND d.appid NOT IN (SELECT appid FROM jogo WHERE possuido=1)")]
    alvo = list(dict.fromkeys(list(possuidos) + faltam))
    mapa = itad.mapear(k_itad, alvo, cache, log)
    banco.meta("itad_ids", cache)
    todas = [int(x["id"]) for x in itad.lojas(k_itad, pais)]
    lows = itad.precos(k_itad, pais, list(mapa.values()), todas, log)
    gid_app = {g: a for a, g in mapa.items()}
    banco.con.executemany("UPDATE jogo SET menor_itad=? WHERE appid=?",
                          [(info["hist_all"], gid_app[g]) for g, info in lows.items() if g in gid_app and info.get("hist_all") is not None])
    banco.commit()
    log("   menor historico de %d itens da biblioteca" % len(lows))


def _cache_itad(cfg, banco):
    cache = banco.meta("itad_ids") or {}
    pasta = (cfg.get("pasta_kurokami_precos") or "").strip()
    arq = os.path.join(pasta, "cache", "itad_ids.json") if pasta else None
    if arq and os.path.isfile(arq) and not cache:
        try:
            with open(arq, encoding="utf-8") as f:
                cache.update(json.load(f))
        except (OSError, json.JSONDecodeError):
            pass
    return cache


def coletar_itad(cfg, banco, wl, chave, importar_hist, log):
    pais = cfg["pais"]
    achadas, faltando, todas = itad.resolver_lojas(chave, pais, cfg["lojas"])
    if faltando:
        log("   fora da ITAD (%s): %s - sem preco por loja para elas" % (pais, ", ".join(faltando)))
    # coleta de todas as lojas (custa o mesmo numero de chamadas); o config so filtra exibicao e alertas,
    # entao marcar uma loja nova no painel ja mostra o historico dela, sem reimportar nada
    shop_ids = sorted(int(x["id"]) for x in todas)
    banco.meta("lojas_itad", sorted((x.get("title") for x in todas), key=str.lower))
    marcadas = set(achadas.values())
    cache = _cache_itad(cfg, banco)
    mapa = itad.mapear(chave, wl, cache, log)
    banco.meta("itad_ids", cache)
    for a, g in mapa.items():
        banco.definir_itad(a, g)
    log("ITAD: %d jogos mapeados | coletando %d lojas, alertando em: %s" % (len(mapa), len(shop_ids), ", ".join(sorted(marcadas))))


    # historico (uma vez por jogo)
    if importar_hist:
        ja = {r["appid"] for r in banco.q("SELECT appid FROM historico_importado WHERE escopo='todas'")}
        novos = [a for a in mapa if a not in ja]
        if novos:
            log("ITAD: importando historico de %d jogos (so na primeira vez)..." % len(novos))
            seguidas = 0
            for i, a in enumerate(novos, 1):
                progresso.passo(i, len(novos))
                try:
                    regs = itad.historico(chave, pais, mapa[a], shop_ids, cfg["historico"]["importar_dias"])
                    banco.importar_historico(a, regs)
                    seguidas = 0
                except itad.ChaveRecusada:
                    raise
                except Exception:
                    seguidas += 1
                    log("   historico do appid %s ficou para a proxima rodada (a ITAD limitou o ritmo)" % a)
                    if seguidas >= 5:
                        log("   a ITAD segue limitando; paro a importacao aqui e continuo na proxima rodada")
                        break
                if i % 50 == 0:
                    banco.commit()
                    log("   %d/%d" % (i, len(novos)))
            banco.commit()

    por_gid = itad.precos(chave, pais, list(mapa.values()), shop_ids, log)
    gid_app = {g: a for a, g in mapa.items()}
    ofertas, novas = {}, 0
    for gid, info in por_gid.items():
        a = gid_app.get(gid)
        if a is None:
            continue
        ofertas[a] = info["ofertas"]
        for o in info["ofertas"]:
            if banco.registrar_preco(a, o["loja"], o["preco"], o["cheio"], o["corte"], "itad", o["url"]):
                novas += 1
    banco.salvar_ofertas_atuais(ofertas)
    banco.meta("ult_itad", agora())
    log("ITAD: precos de %d jogos (%d mudancas registradas)" % (len(ofertas), novas))
    return ofertas, marcadas
