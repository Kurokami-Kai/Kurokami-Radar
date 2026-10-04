"""
KUROKAMI RADAR - linha de comando (o app instalado usa os mesmos comandos: KurokamiRadar.exe <comando>)
Uso:
  py radar.py bandeja             abre o Radar na bandeja: checa sozinho, notifica e serve o painel (pyw = sem janela)
  py radar.py painel              so o painel no navegador, sem a bandeja (http://127.0.0.1:8787)
  py radar.py inicio instalar     abre o Radar sozinho ao entrar no Windows (inicio remover desfaz)
  py radar.py ciclo               uma rodada completa com notificacoes, mostrando tudo no terminal
  py radar.py testar-notificacao  manda uma notificacao de exemplo (--selo: alerta com SELO KUROKAMI)
  py radar.py chaves              grava/atualiza as chaves no Gerenciador de Credenciais
  py radar.py testar              testa as chaves salvas, uma por uma
  py radar.py lojas               lista as lojas da ITAD no Brasil e marca as monitoradas
  py radar.py sondar [appids]     salva respostas cruas das APIs em dados/sonda (para calibrar)
  py radar.py atualizar [--tudo]  coleta precos e grava no historico
  py radar.py verificar           coleta e mostra o que dispararia notificacao agora
  py radar.py historico <jogo>    historico de precos por loja (appid ou parte do nome)
  py radar.py caminhos <jogo>     formas de comprar: base, edicoes, bundles, custo do completo
  py radar.py dlcs <jogo>         DLCs do jogo e como foram classificadas
  py radar.py classificar <jogo> "<trecho|outro>" <classe>
                                  corrige a classe de DLCs (historia, conteudo, cosmetico, atalho, extra, pacote)
  py radar.py conteudo <jogo> "<edicao>" "<dlcs>"
                                  diz o que vem numa edicao quando a Steam nao informa
"""
import argparse
import io
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radar import VERSAO, analise, caminhos, coleta, config, credenciais, dlc as dlcmod, ggdeals, itad, steam
from radar.banco import Banco


def brl(c):
    return "—" if c is None else ("Grátis" if c == 0 else "R$ %s" % ("%.2f" % (c / 100)).replace(".", ","))


def pedir_chaves_se_faltar():
    falta = credenciais.faltando_obrigatorias()
    if not (config.carregar().get("perfil_steam") or "").strip():
        falta = ["perfil Steam"] + falta
    if not falta:
        return True
    print("Faltam chaves: %s. Abrindo a janela de cadastro...\n" % ", ".join(falta))
    try:
        from radar import janela_chaves
        janela_chaves.abrir()
    except Exception:
        credenciais.configurar_interativo(so_faltando=True)
    falta = credenciais.faltando_obrigatorias()
    if not (config.carregar().get("perfil_steam") or "").strip():
        falta = ["perfil Steam"] + falta
    if falta:
        print("!! Ainda faltam: %s" % ", ".join(falta))
        return False
    return True


def achar_jogo(banco, termo):
    if termo.isdigit():
        r = banco.um("SELECT * FROM jogo WHERE appid=?", int(termo))
        return [r] if r else []
    return banco.q("SELECT * FROM jogo WHERE nome LIKE ? ORDER BY na_lista DESC, rcount DESC LIMIT 8", "%" + termo + "%")


def cmd_testar(cfg, _):
    from radar.validar import DICAS, testar
    ruins = 0
    for nome, (titulo, _, obrig) in credenciais.CHAVES.items():
        v = credenciais.ler(nome)
        ok, msg = testar(nome, v)
        print("  %-16s %-34s %s" % (titulo, credenciais.mascarar(v), "OK" if ok else msg))
        if ok is False:
            ruins += 1
            print("  %16s dica: %s" % ("", DICAS[nome]))
    if ruins:
        print("\nCorrija com: py radar.py chaves")


def cmd_lojas(cfg, _):
    achadas, faltando, todas = itad.resolver_lojas(credenciais.ler("itad"), cfg["pais"], cfg["lojas"])
    print("Lojas da ITAD para %s (%d):" % (cfg["pais"], len(todas)))
    for s in sorted(todas, key=lambda s: s.get("title", "").lower()):
        print("  %s %4s  %s" % ("●" if int(s["id"]) in achadas else " ", s["id"], s.get("title")))
    if faltando:
        print("\nFora da ITAD no %s: %s." % (cfg["pais"], ", ".join(faltando)))
        print("Essas lojas nao tem preco por loja via API. A GG.deals ainda pode pegar o preco delas")
        print("dentro do 'melhor preco oficial', mas sem dizer de qual loja veio.")


def cmd_sondar(cfg, args):
    """Respostas cruas, sem chaves e sem dados pessoais, para conferir os formatos."""
    caminhos.garantir()
    apps = [int(a) for a in args.appids] or [1659040, 1971870, 10]
    pais = cfg["pais"]
    k_s, k_i, k_g = credenciais.ler("steam"), credenciais.ler("itad"), credenciais.ler("ggdeals")
    out = {}

    def tenta(nome, f):
        try:
            out[nome] = f()
            print("  ok   %s" % nome)
        except Exception as e:
            out[nome] = {"ERRO": repr(e)}
            print("  ERRO %s: %s" % (nome, e))

    print("Sondando com %s..." % apps)
    tenta("steam_getitems", lambda: steam.get_items([{"appid": a} for a in apps], pais))
    itens = out.get("steam_getitems") if isinstance(out.get("steam_getitems"), list) else []
    bids = [o.get("bundleid") for i in itens for o in (i.get("purchase_options") or []) if o.get("bundleid")][:3]
    pids = [o.get("packageid") for i in itens for o in (i.get("purchase_options") or []) if o.get("packageid")][:3]
    tenta("loja_packagedetails", lambda: {pid: steam._pacotes_uma_chamada([pid], pais) for pid in pids})
    tenta("steam_bundles", lambda: steam.get_items([{"bundleid": b} for b in bids] + [{"packageid": p} for p in pids],
                                                   pais, {"include_included_items": True}))
    sid = None
    try:
        sid = steam.resolver_steamid(k_s, cfg["perfil_steam"])
    except Exception as e:
        print("  ERRO steamid: %s" % e)
    if sid:
        tenta("steam_dlcforapps", lambda: steam.servico_steam(
            steam.API + "IStoreBrowseService/GetDLCForApps/v1/",
            {"steamid": sid, "appids": [{"appid": a} for a in apps], "context": {"country_code": pais}}, k_s))
        tenta("steam_wishlist_resumo", lambda: (lambda w: {"total": len(w), "primeiros": w[:5]})(steam.wishlist(k_s, sid)))
    if k_i:
        tenta("itad_lojas", lambda: itad.lojas(k_i, pais))
        tenta("itad_lookup", lambda: itad._post("lookup/id/shop/61/v1", k_i, ["app/%d" % a for a in apps]))
        gids = [g for g in (out.get("itad_lookup") or {}).values() if isinstance(g, str)]
        if gids:
            tenta("itad_prices_v3", lambda: itad._post("games/prices/v3", k_i, gids, country=pais, nondeals="true"))
            tenta("itad_history_v2", lambda: itad._get("games/history/v2", k_i, id=gids[0], country=pais)[:40])
            tenta("itad_bundles_v2", lambda: itad._get("games/bundles/v2", k_i, id=gids[0], country=pais))
    if k_g:
        tenta("gg_prices", lambda: ggdeals.http_json(ggdeals.API + "?" + ggdeals.urllib.parse.urlencode(
            {"ids": ",".join(map(str, apps)), "key": k_g, "region": pais.lower()})))
    arq = os.path.join(caminhos.SONDA, "sonda.json")
    with open(arq, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nSalvo em %s (%.0f KB). Pode me mandar esse arquivo: nao tem chave nem dado pessoal."
          % (arq, os.path.getsize(arq) / 1024))


def cmd_atualizar(cfg, args):
    b = Banco()
    coleta.atualizar(cfg, b, forcar=args.tudo, importar_hist=not args.sem_historico, sem_limite=args.sem_limite)


def cmd_verificar(cfg, args):
    b = Banco()
    ofertas, gg, marcadas = coleta.atualizar(cfg, b, forcar=args.tudo, importar_hist=not args.sem_historico, sem_limite=args.sem_limite)
    ctx = analise.Contexto(b, cfg)
    al = analise.avaliar(ctx, ofertas, gg, marcadas)
    ult = b.meta("ultimos_alertas") or {}
    b.meta("ultimos_alertas", {"quando": __import__("radar.banco", fromlist=["agora"]).agora(), "itens": al,
                               "novos": ult.get("novos") or []})
    b.commit()
    print("\n" + "=" * 78)
    print(" %d jogo(s) dispararia(m) alerta agora" % len(al))
    print("=" * 78)
    for a in al:
        print(" %-38.38s %-18.18s %11s %5s  score %5s" % (
            a["nome"], a["loja"], brl(a["preco"]), ("-%d%%" % a["corte"]) if a["corte"] else "", a["score"] if a["score"] is not None else "—"))
        print("   %s%s" % (a["motivo"], ("  (também: %s)" % ", ".join(a["outras"])) if a.get("outras") else ""))


def cmd_historico(cfg, args):
    b = Banco()
    achados = achar_jogo(b, " ".join(args.jogo))
    if not achados:
        print("Jogo nao encontrado no banco. Rode py radar.py atualizar antes.")
        return
    j = achados[0]
    print("%s (appid %d)" % (j["nome"], j["appid"]))
    lojas = b.q("SELECT loja, MIN(preco) m, COUNT(*) n FROM preco WHERE appid=? GROUP BY loja ORDER BY m", j["appid"])
    if not args.todas:  # por padrao, so as lojas marcadas + calculos proprios
        alvo = {l.lower() for l in cfg["lojas"]} | {analise.LOJA_COMPLETO.lower(), "steam (direto)",
                                                     analise.LOJA_GG_KEYSHOP.lower(), analise.LOJA_GG_OFICIAL.lower()}
        escondidas = sum(1 for l in lojas if l["loja"].lower() not in alvo)
        lojas = [l for l in lojas if l["loja"].lower() in alvo]
        if escondidas:
            print("  (mais %d lojas com historico; veja com --todas)" % escondidas)
    for l in lojas:
        print("\n  %s  — menor: %s  (%d registros)" % (l["loja"], brl(l["m"]), l["n"]))
        for r in b.q("SELECT * FROM preco WHERE appid=? AND loja=? ORDER BY quando DESC LIMIT ?", j["appid"], l["loja"], args.n):
            marca = "  ◄ menor" if r["preco"] == l["m"] else ""
            print("    %s  %10s  %s%s" % (r["quando"][:10], brl(r["preco"]), ("-%d%%" % r["corte"]) if r["corte"] else "    ", marca))
    if len(achados) > 1:
        print("\nOutros resultados: " + "; ".join("%s (%d)" % (r["nome"], r["appid"]) for r in achados[1:]))


def cmd_caminhos(cfg, args):
    b = Banco()
    achados = achar_jogo(b, " ".join(args.jogo))
    if not achados:
        print("Jogo nao encontrado. Rode py radar.py atualizar antes.")
        return
    j = achados[0]
    ctx = analise.Contexto(b, cfg)
    rel = ctx.relevantes(j["appid"])
    print("%s — modo: %s — conteúdo relevante: base + %d DLCs" % (j["nome"], config.modo_do_jogo(cfg, j["appid"]), len(rel)))
    print("  %-46s %10s %6s %14s" % ("opção", "seu preço", "cobre", "p/ completar"))
    for c in ctx.caminhos(j["appid"]):
        extra = ""
        if c.get("itens_que_voce_tem"):
            extra += "  (você já tem %d de %d itens)" % (c["itens_que_voce_tem"], c["itens_total"])
        if c.get("extras_lista"):
            extra += "  +%d da sua lista" % len(c["extras_lista"])
        est = "~" if c.get("estimada") else " "
        print("  %-46.46s %10s %4d%%%s %14s%s" % (c["nome"], brl(c["preco"]), c["cobertura"], est, brl(c["custo_completo"]), extra))
        if args.itens and c["id"] in ctx.opcoes:
            for a in ctx.opcoes[c["id"]]["itens"]:
                jj = ctx.jogos.get(a) or {}
                marca = "base" if a == j["appid"] else ("relevante" if a in rel else ("você tem" if a in ctx.possuidos else ""))
                print("        - %-50.50s %s" % (jj.get("nome") or a, marca))
    if any(c.get("estimada") and c["tipo"] != "parcial" for c in ctx.caminhos(j["appid"])):
        print("\n  ~ conteudo da edicao nao confirmado pela Steam: contei so o jogo base.")
        print('    Se souber o que vem nela: py radar.py conteudo %s "Deluxe Edition" "Deluxe Pack|Seven Deadly"' % args.jogo[0])
    m = ctx.melhor_combinacao(j["appid"])
    if m:
        print("\n  Jeito mais barato de ter tudo: %s" % brl(m["custo_completo"]))
        for nome, preco in m["partes"]:
            print("    %10s  %s" % (brl(preco), nome))
        for a, preco in m["avulsos"]:
            print("    %10s  %s (avulso)" % (brl(preco), (ctx.jogos.get(a) or {}).get("nome") or a))
    else:
        print("\n  Nao da para completar: algum item nao e vendido avulso nem aparece em bundle/edicao.")


def cmd_dlcs(cfg, args):
    b = Banco()
    achados = achar_jogo(b, " ".join(args.jogo))
    if not achados:
        print("Jogo nao encontrado.")
        return
    j = achados[0]
    rows = b.q("SELECT d.*, j.nome, j.preco_steam FROM dlc d LEFT JOIN jogo j ON j.appid=d.appid WHERE d.pai=? ORDER BY d.classe, j.preco_steam DESC", j["appid"])
    print("%s — %d DLCs" % (j["nome"], len(rows)))
    for r in rows:
        ign = dlcmod.ignorada(r["classe"], r["preco_steam"], cfg["dlc"])
        print("  %s %-24s %10s  %s" % ("·" if ign else "●", dlcmod.CLASSES.get(r["classe"], r["classe"]), brl(r["preco_steam"]), r["nome"]))
    print("\n● entra no custo completo   · ignorada pelas opções do config")
    print('Para corrigir: py radar.py classificar "%s" "Trinity|Street Art" cosmetico' % j["nome"].split(":")[0][:30])


def menu():
    print("KUROKAMI RADAR %s\n" % VERSAO)
    opcoes = [("Abrir na bandeja (checa, notifica e serve o painel)", ["bandeja"]), ("Abrir só o painel", ["painel"]), ("Verificar promoções agora", ["verificar"]),
              ("Iniciar com o Windows", ["inicio", "instalar"]), ("Testar notificação", ["testar-notificacao"]),
              ("Cadastrar / trocar chaves", ["chaves"]),
              ("Testar chaves", ["testar"]), ("Lojas da ITAD", ["lojas"]),
              ("Histórico de um jogo", ["historico"]), ("Formas de comprar um jogo", ["caminhos"]),
              ("DLCs de um jogo", ["dlcs"])]
    for i, (t, _) in enumerate(opcoes, 1):
        print("  %d. %s" % (i, t))
    while True:
        r = input("\nEscolha: ").strip()
        if r.isdigit() and 1 <= int(r) <= len(opcoes):
            cmd = list(opcoes[int(r) - 1][1])
            if cmd[0] in ("historico", "caminhos", "dlcs"):
                cmd += input("Nome ou appid do jogo: ").strip().split() or ["?"]
            print()
            return cmd


def cmd_conteudo(cfg, args):
    """py radar.py conteudo hitman "Deluxe Edition" "Deluxe Pack|Seven Deadly"
    Diz manualmente o que vem numa edicao, quando a Steam nao informa."""
    import re
    b = Banco()
    achados = achar_jogo(b, args.jogo)
    if not achados:
        print("Jogo nao encontrado.")
        return
    j = achados[0]
    eds = [dict(r) for r in b.q("SELECT o.* FROM opcao o JOIN jogo_opcao jo ON jo.opcao=o.id WHERE jo.appid=? AND o.tipo='edicao'", j["appid"])]
    ed = [e for e in eds if re.search(args.edicao, e["nome"] or "", re.I)]
    if len(ed) != 1:
        print("Edicoes de %s: %s" % (j["nome"], "; ".join(e["nome"] for e in eds) or "nenhuma"))
        print("O trecho '%s' achou %d. Use um trecho que pegue so uma." % (args.edicao, len(ed)))
        return
    ed = ed[0]
    rx = re.compile(args.dlcs, re.I)
    dl = b.q("SELECT d.appid, j.nome FROM dlc d JOIN jogo j ON j.appid=d.appid WHERE d.pai=?", j["appid"])
    itens = [j["appid"]] + [r["appid"] for r in dl if rx.search(r["nome"] or "")]
    b.con.execute("UPDATE opcao SET itens=? WHERE id=?", (json.dumps(itens), ed["id"]))
    manuais = set(b.meta("edicoes_manuais") or [])
    manuais.add(ed["id"])
    b.meta("edicoes_manuais", sorted(manuais))
    b.commit()
    print("%s agora inclui:" % ed["nome"])
    for a in itens:
        r = b.um("SELECT nome FROM jogo WHERE appid=?", a)
        print("  - %s" % (r["nome"] if r else a))
    print("\nEssa definicao nao e sobrescrita pela coleta.")


def cmd_ciclo(cfg, args):
    from radar import servico
    alertas, novos = servico.ciclo(print, forcar=args.tudo)
    print("\nNotificados agora: %d. Lista completa em %s" % (len(novos), caminhos.ARQ_RELATORIO))


def cmd_testar_notificacao(cfg, args):
    from radar import notificar
    from radar.bandeja import desenhar_icone
    caminhos.garantir()
    desenhar_icone().save(caminhos.ARQ_ICONE)
    notificar.registrar_app(caminhos.ARQ_ICONE)
    b = Banco()
    j = b.um("SELECT appid, nome, capa FROM jogo WHERE na_lista=1 AND capa IS NOT NULL ORDER BY rcount DESC LIMIT 1")
    img = notificar.capa(j["appid"], j["capa"]) if j else None
    nome = j["nome"] if j else "Jogo de exemplo"
    url = "https://store.steampowered.com/app/%d/" % j["appid"] if j else "https://store.steampowered.com/"
    if getattr(args, "selo", False):  # passa pelo caminho real dos alertas (titulo, botoes, capa)
        from radar.notificador import Notificador
        Notificador(b, cfg, log=lambda m: None)._enviar(
            {"appid": j["appid"] if j else 0, "nome": nome, "preco": 999, "corte": 90, "loja": "Steam", "url": url,
             "selo": True, "raridade": "lendario", "score": 90,
             "motivo": "Selo Kurokami: Lendário: nunca chegou a -85% (TESTE)"})
        print("Notificação de Selo enviada. Se não apareceu em uns segundos, veja Configurações > Sistema > Notificações")
        return
    ok = notificar.mostrar(nome, "R$ 9,99 · -90% na Steam (TESTE)\nNo menor histórico · score 88",
                           clique=url, botoes=[("Abrir oferta", url)], imagem=img, rodape="notificação de teste")
    print("Notificação enviada. Se não apareceu em uns segundos, veja Configurações > Sistema > Notificações"
          if ok else "Falhou ao chamar o PowerShell.")


def cmd_inicio(cfg, args):
    from radar import inicio
    print(inicio.instalar() if args.acao == "instalar" else inicio.remover())


def cmd_classificar(cfg, args):
    """py radar.py classificar hitman "Trinity|Street Art|Makeshift" cosmetico"""
    import re
    b = Banco()
    if args.classe not in dlcmod.CLASSES:
        print("Classe invalida. Use uma de: %s" % ", ".join(dlcmod.CLASSES))
        return
    achados = achar_jogo(b, args.jogo)
    if not achados:
        print("Jogo nao encontrado.")
        return
    j = achados[0]
    rx = re.compile(args.trecho, re.I)
    rows = b.q("SELECT d.appid, j.nome FROM dlc d JOIN jogo j ON j.appid=d.appid WHERE d.pai=?", j["appid"])
    alvo = [r for r in rows if rx.search(r["nome"] or "")]
    if not alvo:
        print("Nenhuma DLC de %s bate com '%s'." % (j["nome"], args.trecho))
        return
    for r in alvo:
        b.con.execute("UPDATE dlc SET classe=?, origem='usuario' WHERE appid=?", (args.classe, r["appid"]))
        print("  %-24s %s" % (dlcmod.CLASSES[args.classe], r["nome"]))
    b.commit()
    print("\n%d DLC(s) marcadas. Essa escolha nao e sobrescrita pela classificacao automatica." % len(alvo))


def main():
    ap = argparse.ArgumentParser(prog="radar", description="Kurokami Radar %s" % VERSAO)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("chaves"); s.add_argument("--terminal", action="store_true", help="sem janela, digitando no terminal")
    sub.add_parser("testar")
    sub.add_parser("lojas")
    s = sub.add_parser("sondar"); s.add_argument("appids", nargs="*")
    for nome in ("atualizar", "verificar"):
        s = sub.add_parser(nome)
        s.add_argument("--tudo", action="store_true", help="ignora os intervalos e consulta tudo")
        s.add_argument("--sem-historico", action="store_true", help="nao importa historico antigo da ITAD")
        s.add_argument("--sem-limite", action="store_true", help="faz todas as consultas lentas da loja de uma vez")
    s = sub.add_parser("historico"); s.add_argument("jogo", nargs="+"); s.add_argument("-n", type=int, default=12)
    s.add_argument("--todas", action="store_true", help="mostra todas as lojas, nao so as marcadas")
    s = sub.add_parser("caminhos"); s.add_argument("jogo", nargs="+")
    s.add_argument("--itens", action="store_true", help="lista o que vem em cada bundle/edicao")
    s = sub.add_parser("dlcs"); s.add_argument("jogo", nargs="+")
    s = sub.add_parser("classificar"); s.add_argument("jogo"); s.add_argument("trecho"); s.add_argument("classe")
    s = sub.add_parser("conteudo"); s.add_argument("jogo"); s.add_argument("edicao"); s.add_argument("dlcs")
    sub.add_parser("atualizar-app", help="procura e instala a versao nova do Radar")
    s = sub.add_parser("bandeja"); s.add_argument("--esperar", action="store_true", help=argparse.SUPPRESS)
    s.add_argument("--abrir", action="store_true", help="abre o painel no navegador ao iniciar")
    sub.add_parser("painel")
    s = sub.add_parser("ciclo"); s.add_argument("--tudo", action="store_true")
    s = sub.add_parser("testar-notificacao")
    s.add_argument("--selo", action="store_true", help="simula um alerta com SELO KUROKAMI (passa pelo notificador)")
    s = sub.add_parser("inicio"); s.add_argument("acao", choices=["instalar", "remover"])
    if len(sys.argv) == 1 and getattr(sys, "frozen", False):
        if sys.stdout is None or "bandeja" in os.path.basename(sys.executable).lower():
            sys.argv.append("bandeja")  # instalado (sem console): abrir = ir para a bandeja
        else:
            sys.argv += menu()  # aberto com duplo clique: menu em vez de linha de comando
    args = ap.parse_args()
    if not args.cmd:
        print(__doc__)
        return
    caminhos.garantir()
    cfg = config.carregar()
    if args.cmd == "chaves":
        if credenciais.keyring is None:
            print("Instale o keyring antes: py -m pip install keyring")
            return
        if not args.terminal:
            try:
                from radar import janela_chaves
                janela_chaves.abrir()
                cmd_testar(cfg, args)
                return
            except Exception as e:
                print("Nao consegui abrir a janela (%s). Indo pelo terminal." % e)
        credenciais.configurar_interativo()
        return
    if args.cmd == "testar":
        cmd_testar(cfg, args)
        return
    if args.cmd == "atualizar-app":
        from radar import atualizador
        atualizador.janela()
        return
    if args.cmd == "painel":
        from radar import painel
        try:
            painel.iniciar(abrir=True)
        except OSError:
            import webbrowser
            webbrowser.open(painel.url())
            print("O painel ja esta aberto pela bandeja: %s" % painel.url())
            return
        print("Painel em %s  (Ctrl+C para fechar)" % painel.url())
        import time
        while True:
            time.sleep(3600)
    if args.cmd == "bandeja":
        from radar import bandeja
        bandeja.main(esperar=getattr(args, "esperar", False), abrir=getattr(args, "abrir", False))
        return
    if args.cmd in ("lojas", "sondar", "atualizar", "verificar", "ciclo") and not pedir_chaves_se_faltar():
        return
    {"lojas": cmd_lojas, "sondar": cmd_sondar, "atualizar": cmd_atualizar, "verificar": cmd_verificar,
     "historico": cmd_historico, "caminhos": cmd_caminhos, "dlcs": cmd_dlcs,
     "classificar": cmd_classificar, "conteudo": cmd_conteudo, "ciclo": cmd_ciclo,
     "testar-notificacao": cmd_testar_notificacao, "inicio": cmd_inicio}[args.cmd](cfg, args)


if __name__ == "__main__":
    duplo_clique = len(sys.argv) == 1 and getattr(sys, "frozen", False) and sys.stdout is not None \
        and "bandeja" not in sys.executable.lower()
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido.")
    except Exception as e:
        print("\n!! Erro: %s" % e)
        import traceback
        traceback.print_exc()
    if duplo_clique and sys.stdin is not None:
        input("\nAperte Enter para fechar...")
