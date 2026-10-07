"""Teste de viabilidade do login Steam por QR (spec 06, Etapa 1). O app NAO muda.

Uso (precisa de `qrcode`; use um venv fora do Python do sistema):
    python tools/teste_login_steam.py            # login por QR + carrinho, lista, seguidos, familia, sair
    python tools/teste_login_steam.py --celular  # so o teste "abrir o link do desafio no celular" + sair
Regras: so HTTPS para api.steampowered.com, login.steampowered.com e store.steampowered.com; 1 chamada/s;
toda acao que muda a conta e fotografada, feita, desfeita e conferida; token nenhum vai para arquivo ou log
(so os 6 primeiros caracteres + "..."). Resultado bruto sem tokens: dados/sonda/login_steam.json (fora do Git)."""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from radar import rede  # noqa: E402

API = "https://api.steampowered.com/"
LOJA = "https://store.steampowered.com/"
PERMITIDOS = {"api.steampowered.com", "login.steampowered.com", "store.steampowered.com"}
SONDA = os.path.join(RAIZ, "dados", "sonda")
SAIDA = os.path.join(SONDA, "login_steam.json")
RITMO = rede.Ritmo(1.0, piso=1.0)   # no maximo 1 chamada por segundo
RES = {"quando": datetime.now(timezone.utc).isoformat(timespec="seconds"), "itens": {}, "chamadas": []}
SEGREDOS = set()                    # tokens vistos: mascarados em qualquer texto que vire log/arquivo
PAIS = "BR"


def mask(v):
    return (str(v)[:6] + "...") if v else "(vazio)"


def limpa(txt):
    txt = str(txt)
    for s in SEGREDOS:
        if s:
            txt = txt.replace(s, mask(s))
    return txt


def log(*a):
    print(limpa(" ".join(str(x) for x in a)), flush=True)


def salvar():
    os.makedirs(SONDA, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(limpa(json.dumps(RES, ensure_ascii=False, indent=1, default=str)))


def item(nome, **dados):
    RES["itens"].setdefault(nome, {}).update(dados)
    salvar()


def jwt(tok):
    """Corpo do JWT sem verificar a assinatura."""
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def data(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def chamar(servico, metodo, entrada=None, post=False, token=None, versao="v1", cookie=None, url=None):
    """Uma chamada. Devolve (resposta_json|None, eresult, segundos, erro)."""
    if url is None:
        url = "%s%s/%s/%s/" % (API, servico, metodo, versao)
    host = urllib.parse.urlparse(url).hostname
    assert host in PERMITIDOS and url.startswith("https://"), "host nao permitido: %s" % host
    params = {}
    if entrada is not None:
        params["input_json"] = json.dumps(entrada, separators=(",", ":"))
    if token:
        params["access_token"] = token
    cab = {"User-Agent": rede.UA, "Accept": "application/json"}
    if cookie:
        cab["Cookie"] = cookie
    if post:
        dados, alvo = urllib.parse.urlencode(params).encode(), url
        cab["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        dados, alvo = None, url + ("?" + urllib.parse.urlencode(params) if params else "")
    RITMO.aguardar()
    t0 = time.monotonic()
    eres, erro, corpo = None, None, None
    for n in range(3):
        try:
            req = urllib.request.Request(alvo, data=dados, headers=cab, method="POST" if post else "GET")
            with urllib.request.urlopen(req, timeout=45) as r:
                eres = r.headers.get("X-eresult")
                txt = r.read().decode("utf-8", "replace")
            corpo = json.loads(txt) if txt.strip() else {}
            erro = None
            break
        except urllib.error.HTTPError as e:
            eres = e.headers.get("X-eresult")
            erro = "HTTP %s %s" % (e.code, (e.read().decode("utf-8", "replace")[:200]).strip())
            if e.code == 429 or e.code >= 500:
                time.sleep(3 * (n + 1))
                RITMO.freio(3)
                continue
            break
        except Exception as e:  # rede, JSON
            erro = "%s: %s" % (type(e).__name__, e)
            time.sleep(2)
    seg = round(time.monotonic() - t0, 2)
    RES["chamadas"].append({"m": "%s/%s" % (servico or "-", metodo or url.split("/")[-2] if url else "-"),
                            "post": post, "eresult": eres, "s": seg, "erro": erro})
    if erro:
        log("   !", servico, metodo, "->", erro, "(eresult %s)" % eres)
    return (corpo or {}).get("response", corpo), eres, seg, erro


def passo(nome, fn):
    """Roda uma etapa; um erro nela nao derruba as outras."""
    log("\n== %s" % nome)
    try:
        fn()
    except Exception as e:
        log("   ERRO na etapa:", type(e).__name__, e)
        item(nome, erro="%s: %s" % (type(e).__name__, e))


# ------------------------------------------------------------------ 1. login
class Sessao:
    refresh = access = steamid = None
    conta = None
    platform = None


S = Sessao()


def qr_janela(url, funcao):
    """Mostra o QR numa janela que troca sozinha quando a Steam renova o desafio (a cada ~20 s);
    roda funcao() numa thread e fecha a janela quando ela termina. Devolve o que funcao devolveu."""
    import threading
    import tkinter as tk
    import qrcode
    from PIL import ImageTk
    os.makedirs(SONDA, exist_ok=True)
    estado = {"url": url, "novo": True, "fim": False, "res": None}

    def trabalho():
        try:
            estado["res"] = funcao(lambda u: estado.update(url=u, novo=True))
        finally:
            estado["fim"] = True
    root = tk.Tk()
    root.title("Kurokami Radar - escaneie com o app da Steam")
    lab = tk.Label(root)
    lab.pack()
    tk.Label(root, text="O QR troca sozinho a cada ~20 s. Escaneie e confirme no app.").pack()

    def ciclo():
        if estado["novo"]:
            estado["novo"] = False
            img = ImageTk.PhotoImage(qrcode.make(estado["url"]).resize((420, 420)))
            lab.configure(image=img)
            lab.image = img
        if estado["fim"]:
            root.destroy()
        else:
            root.after(500, ciclo)
    threading.Thread(target=trabalho, daemon=True).start()
    root.attributes("-topmost", True)
    ciclo()
    root.mainloop()
    return estado["res"]


def iniciar_qr(plataforma, nome="Kurokami Radar (teste)"):
    entrada = {"device_friendly_name": nome, "platform_type": plataforma, "website_id": "Store",
               "device_details": {"device_friendly_name": nome, "platform_type": plataforma}}
    r, eres, seg, erro = chamar("IAuthenticationService", "BeginAuthSessionViaQR", entrada, post=True)
    if erro or not r.get("challenge_url"):
        return None, seg, erro or "sem challenge_url (eresult %s)" % eres
    return r, seg, None


def aguardar(r, limite=180, ao_renovar=None):
    """Poll ate aprovar. Devolve o response do ultimo Poll bem-sucedido."""
    client_id, request_id = r["client_id"], r["request_id"]
    fim = time.monotonic() + limite
    espera = max(float(r.get("interval") or 5), 2.0)
    while time.monotonic() < fim:
        time.sleep(espera)
        p, eres, seg, erro = chamar("IAuthenticationService", "PollAuthSessionStatus",
                                    {"client_id": client_id, "request_id": request_id}, post=True)
        if erro:
            return None
        if p.get("new_client_id"):
            client_id = p["new_client_id"]   # a Steam troca o desafio de tempos em tempos
            if p.get("new_challenge_url") and not p.get("refresh_token") and ao_renovar:
                ao_renovar(p["new_challenge_url"])
        if p.get("refresh_token"):
            return p
    return None


def login():
    plat_ok = None
    for plataforma in (2, 1, 3):   # 2 = WebBrowser (o que a loja aceita)
        r, seg, erro = iniciar_qr(plataforma)
        item("1 Login: BeginAuthSessionViaQR platform_type=%s" % plataforma, ok=not erro, s=seg, erro=erro,
             campos=sorted(r.keys()) if r else None)
        if r:
            plat_ok = plataforma
            break
    if not r:
        raise RuntimeError("BeginAuthSessionViaQR falhou")
    S.platform = plat_ok
    log("   QR criado (platform_type=%s, %ss). Escaneie com o app da Steam (tem ate 3 min)." % (plat_ok, seg))
    log("   allowed_confirmations:", [c.get("confirmation_type") for c in r.get("allowed_confirmations", [])])
    p = qr_janela(r["challenge_url"], lambda cb: aguardar(r, ao_renovar=cb))
    if not p:
        raise RuntimeError("QR nao foi aprovado em 3 minutos (ou o Poll falhou)")
    S.refresh, S.access, S.conta = p["refresh_token"], p.get("access_token"), p.get("account_name")
    SEGREDOS.update([S.refresh, S.access])
    jr = jwt(S.refresh)
    S.steamid = jr["sub"]
    SEGREDOS.add(S.steamid) if False else None
    ja = jwt(S.access) if S.access else {}
    log("   Aprovado. SteamID final ...%s | refresh vence %s | access vence %s" % (
        S.steamid[-4:], data(jr["exp"]), data(ja["exp"]) if ja else "(sem access)"))
    item("1 Login", plataforma_que_funcionou=plat_ok, steamid_final=S.steamid[-4:],
         refresh_exp=data(jr["exp"]), refresh_aud=jr.get("aud"),
         access_exp=data(ja["exp"]) if ja else None, access_aud=ja.get("aud"),
         refresh_validade_dias=round((jr["exp"] - time.time()) / 86400, 1),
         access_validade_min=round((ja["exp"] - time.time()) / 60) if ja else None,
         poll_campos=sorted(p.keys()), conta_login="%s..." % (S.conta or "")[:2])
    if not S.access:   # o Poll nem sempre devolve access_token: renova
        renovar()


def renovar(extra=None):
    ent = {"refresh_token": S.refresh, "steamid": S.steamid}
    ent.update(extra or {})
    r, eres, seg, erro = chamar("IAuthenticationService", "GenerateAccessTokenForApp", ent, post=True)
    if erro or not (r or {}).get("access_token"):
        item("1 Renovacao", ok=False, s=seg, erro=erro or "sem access_token (eresult %s)" % eres)
        return False
    S.access = r["access_token"]
    SEGREDOS.add(S.access)
    if r.get("refresh_token"):
        SEGREDOS.add(r["refresh_token"])
    ja = jwt(S.access)
    item("1 Renovacao", ok=True, s=seg, access_exp=data(ja["exp"]),
         access_validade_min=round((ja["exp"] - time.time()) / 60), devolveu_refresh_novo=bool(r.get("refresh_token")),
         extra=extra)
    log("   renovou: access vence %s (em %s min)%s" % (data(ja["exp"]), round((ja["exp"] - time.time()) / 60),
                                                       "; veio refresh novo" if r.get("refresh_token") else ""))
    return True


def tokens_enumerar():
    r, eres, seg, erro = chamar("IAuthenticationService", "EnumerateTokens", {"include_revoked": False},
                                post=True, token=S.access)
    if erro:
        return None
    return r


# ------------------------------------------------------------------ 4a. userdata (precisa antes do carrinho)
USERDATA = {}


def ler_userdata():
    ck = "steamLoginSecure=%s%%7C%%7C%s" % (S.steamid, S.access)
    r, eres, seg, erro = chamar(None, None, None, cookie=ck, url=LOJA + "dynamicstore/userdata/")
    if erro or not isinstance(r, dict):
        item("4 Ignorados (userdata)", ok=False, s=seg, erro=erro)
        return
    USERDATA.update(r)
    item("4 Ignorados (userdata)", ok=bool(r.get("rgOwnedApps") is not None), s=seg,
         chaves=sorted(r.keys())[:40], logado=bool(r.get("rgOwnedApps")))
    log("   userdata: %d na lista, %d seguidos, %d ignorados, %d jogos/pacotes, %d no carrinho (%ss)" % (
        len(r.get("rgWishlist") or []), len(r.get("rgFollowedApps") or []),
        len(r.get("rgIgnoredApps") or {}), len(r.get("rgOwnedApps") or []), len(r.get("rgAppsInCart") or []), seg))


# ------------------------------------------------------------------ 3. lista de desejos (leitura)
def wl_publica():
    r, eres, seg, erro = chamar("IWishlistService", "GetWishlist", {"steamid": S.steamid})
    return (r or {}).get("items") or [], seg, erro


def wl_token():
    r, eres, seg, erro = chamar("IWishlistService", "GetWishlist", {"steamid": S.steamid}, token=S.access)
    return (r or {}).get("items") or [], seg, erro


def lista_leitura():
    pub, s1, e1 = wl_publica()
    tok, s2, e2 = wl_token()
    ap, at = [i["appid"] for i in pub], [i["appid"] for i in tok]
    prio_p = {i["appid"]: i.get("priority") for i in pub}
    prio_t = {i["appid"]: i.get("priority") for i in tok}
    item("3 Lista de desejos: leitura", publica=len(pub), com_token=len(tok), s_publica=s1, s_token=s2,
         mesma_ordem=ap == at, mesmos_itens=set(ap) == set(at), mesmas_prioridades=prio_p == prio_t,
         erro_publica=e1, erro_token=e2,
         perfil_privado="nao testado sem mudar a privacidade do perfil: fica para a Etapa 2")
    log("   publica %d itens, com token %d itens; mesma ordem: %s; mesmas prioridades: %s" % (
        len(pub), len(tok), ap == at, prio_p == prio_t))
    RES["_wl"] = ap  # so appids publicos


# ------------------------------------------------------------------ 2. carrinho
def get_cart():
    r, eres, seg, erro = chamar("IAccountCartService", "GetCart", {"user_country": PAIS}, token=S.access)
    if erro:
        return None, seg, erro
    itens = (r or {}).get("cart", {}).get("line_items") or []
    return itens, seg, None


def chaves(itens):
    return sorted((i.get("packageid") or 0, i.get("bundleid") or 0) for i in itens)


def acha_pacotes(max_jogos=25):
    """(appid, nome, packageid) de jogos pagos da lista que o dono nao tem, via appdetails (loja)."""
    dono = set(USERDATA.get("rgOwnedApps") or [])
    achados = []
    for appid in (RES.get("_wl") or [])[:60]:
        if appid in dono:
            continue
        r, eres, seg, erro = chamar(None, None, None, url="%sapi/appdetails?appids=%s&cc=br&filters=basic,price_overview,packages,package_groups" % (LOJA, appid))
        d = ((r or {}).get(str(appid)) or {}).get("data") if isinstance(r, dict) else None
        if not d or not d.get("price_overview") or d.get("is_free"):
            continue
        subs = [s for g in d.get("package_groups", []) for s in g.get("subs", [])]
        subs = [s for s in subs if s.get("packageid") and not s.get("is_free_license")]
        if not subs:
            continue
        subs.sort(key=lambda s: s.get("price_in_cents_with_discount") or 10 ** 9)
        achados.append((appid, d.get("name"), subs[0]["packageid"], subs[0].get("price_in_cents_with_discount")))
        if len(achados) >= 3:
            break
        RITMO.aguardar()
    return achados


def achar_bundle(appids):
    """bundleid a partir do HTML da pagina da loja (data-ds-bundleid)."""
    for appid in appids[:8]:
        RITMO.aguardar()
        try:
            req = urllib.request.Request("%sapp/%s/?cc=br&l=portuguese" % (LOJA, appid), headers={
                "User-Agent": rede.UA, "Cookie": "birthtime=631152001; lastagecheckage=1-January-1990; wants_mature_content=1"})
            with urllib.request.urlopen(req, timeout=45) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception as e:
            log("   pagina %s: %s" % (appid, e))
            continue
        m = re.findall(r'data-ds-bundleid="(\d+)"', html)
        if m:
            return appid, int(m[0])
    return None, None


def remover_tudo_que_nao_estava(antes_chaves):
    itens, _, _ = get_cart()
    for i in itens or []:
        k = (i.get("packageid") or 0, i.get("bundleid") or 0)
        if k not in antes_chaves:
            chamar("IAccountCartService", "RemoveItemFromCart", {"line_item_id": i["line_item_id"], "user_country": PAIS},
                   post=True, token=S.access)


def carrinho():
    antes, s0, erro = get_cart()
    if antes is None:
        item("2 Carrinho: leitura", ok=False, erro=erro, s=s0)
        return
    ka = chaves(antes)
    item("2 Carrinho: leitura", ok=True, s=s0, itens=len(antes), pacotes=[k[0] for k in ka if k[0]],
         bundles=[k[1] for k in ka if k[1]], campos_item=sorted(antes[0].keys()) if antes else None,
         ids_userdata=USERDATA.get("rgAppsInCart"))
    log("   carrinho antes: %d item(ns) (%ss)" % (len(antes), s0))
    pacotes = acha_pacotes()
    if not pacotes:
        item("2 Carrinho: escrita", ok=False, erro="nao achei jogo pago e nao possuido na lista para o teste")
        return
    log("   jogos de teste:", [(a, n, p) for a, n, p, _ in pacotes])
    try:
        # --- 1 item
        pk = pacotes[0][2]
        r, eres, seg, erro = chamar("IAccountCartService", "AddItemsToCart",
                                    {"user_country": PAIS, "items": [{"packageid": pk}]}, post=True, token=S.access)
        meio, s1, _ = get_cart()
        apareceu = meio is not None and (pk, 0) in chaves(meio)
        validos = [i.get("is_valid") for i in (meio or []) if i.get("packageid") == pk]
        item("2 Carrinho: adicionar 1 pacote", ok=apareceu, s_add=seg, s_get=s1, erro=erro, eresult=eres,
             packageid=pk, is_valid=validos, resposta_campos=sorted((r or {}).keys()),
             verificacao_idade="sem erro de idade nesta chamada" if not erro else None)
        log("   adicionou pacote %s: apareceu=%s valido=%s (%ss)" % (pk, apareceu, validos, seg))
        if apareceu:
            log("   >>> Item no carrinho por 40 s. Abra https://store.steampowered.com/cart/ no navegador e veja se aparece.")
            time.sleep(40)
        li = [i["line_item_id"] for i in (meio or []) if i.get("packageid") == pk]
        for lid in li:
            r, eres, seg, erro = chamar("IAccountCartService", "RemoveItemFromCart",
                                        {"line_item_id": lid, "user_country": PAIS}, post=True, token=S.access)
            item("2 Carrinho: remover 1", s=seg, erro=erro, eresult=eres)
        dep, _, _ = get_cart()
        item("2 Carrinho: volta ao estado inicial (1 item)", ok=dep is not None and chaves(dep) == ka)
        log("   removeu; igual ao inicial:", dep is not None and chaves(dep) == ka)

        # --- varios de uma vez
        if len(pacotes) > 1:
            pks = [p[2] for p in pacotes]
            r, eres, seg, erro = chamar("IAccountCartService", "AddItemsToCart",
                                        {"user_country": PAIS, "items": [{"packageid": p} for p in pks]},
                                        post=True, token=S.access)
            meio, _, _ = get_cart()
            n_ok = sum(1 for p in pks if meio and (p, 0) in chaves(meio))
            item("2 Carrinho: lote de %d pacotes" % len(pks), ok=n_ok == len(pks), entraram=n_ok, s=seg, erro=erro,
                 nota="so testado ate %d itens (nao foi esticado para nao mexer demais na conta)" % len(pks))
            log("   lote de %d: %d entraram (%ss)" % (len(pks), n_ok, seg))
            remover_tudo_que_nao_estava(set(ka))
            dep, _, _ = get_cart()
            item("2 Carrinho: volta ao estado inicial (lote)", ok=dep is not None and chaves(dep) == ka)
            log("   igual ao inicial apos lote:", dep is not None and chaves(dep) == ka)

        # --- bundle
        appb, bid = achar_bundle([p[0] for p in pacotes] + (RES.get("_wl") or [])[:6])
        if not bid:
            item("2 Carrinho: bundle", ok=None, nota="nao achei bundleid na pagina dos jogos testados")
        else:
            r, eres, seg, erro = chamar("IAccountCartService", "AddItemsToCart",
                                        {"user_country": PAIS, "items": [{"bundleid": bid}]}, post=True, token=S.access)
            meio, _, _ = get_cart()
            ok = meio is not None and (0, bid) in chaves(meio)
            item("2 Carrinho: bundle", ok=ok, bundleid=bid, de_appid=appb, s=seg, erro=erro, eresult=eres)
            log("   bundle %s (do app %s): apareceu=%s" % (bid, appb, ok))
            remover_tudo_que_nao_estava(set(ka))
            dep, _, _ = get_cart()
            item("2 Carrinho: volta ao estado inicial (bundle)", ok=dep is not None and chaves(dep) == ka)
            log("   igual ao inicial apos bundle:", dep is not None and chaves(dep) == ka)
    finally:
        remover_tudo_que_nao_estava(set(ka))
        fim, _, _ = get_cart()
        item("2 Carrinho: estado final", igual_ao_inicial=fim is not None and chaves(fim) == ka)


# ------------------------------------------------------------------ 3b. lista de desejos (escrita)
GRATIS = [440, 570, 230410, 238960, 252490, 1172470]   # TF2, Dota 2, Warframe, Path of Exile, Rust(pago, ignorado), Apex


def lista_escrita():
    antes, _, erro = wl_token()
    base = {i["appid"]: i.get("priority") for i in antes}
    alvo = next((a for a in (440, 570, 230410, 238960, 1172470, 553850) if a not in base), None)
    if not alvo:
        item("3 Lista de desejos: escrita", ok=None, nota="todos os candidatos ja estavam na lista")
        return
    try:
        r, eres, s1, e1 = chamar("IWishlistService", "AddToWishlist", {"appid": alvo}, post=True, token=S.access)
        meio, _, _ = wl_token()
        entrou = any(i["appid"] == alvo for i in meio)
        r2, eres2, s2, e2 = chamar("IWishlistService", "RemoveFromWishlist", {"appid": alvo}, post=True, token=S.access)
        depois, _, _ = wl_token()
        igual = {i["appid"]: i.get("priority") for i in depois} == base
        mesma_ordem = [i["appid"] for i in depois] == [i["appid"] for i in antes]
        item("3 Lista de desejos: escrita", ok=entrou and igual, appid_teste=alvo, s_add=s1, s_remove=s2,
             erro_add=e1, erro_remove=e2, contagem_add=(r or {}).get("wishlist_count"),
             contagem_remove=(r2 or {}).get("wishlist_count"), voltou_igual=igual, mesma_ordem=mesma_ordem,
             itens_antes=len(antes), itens_depois=len(depois))
        log("   add %s: entrou=%s; removeu; lista igual (itens e prioridades): %s; mesma ordem: %s" % (
            alvo, entrou, igual, mesma_ordem))
    finally:
        r = wl_token()[0]
        if any(i["appid"] == alvo for i in r):   # garantia de limpeza
            chamar("IWishlistService", "RemoveFromWishlist", {"appid": alvo}, post=True, token=S.access)


# ------------------------------------------------------------------ 4. seguidos
def seguidos():
    r, eres, seg, erro = chamar("IStoreService", "GetGamesFollowed", {"steamid": S.steamid}, token=S.access)
    seg_ids = (r or {}).get("appids") or []
    wl = set(RES.get("_wl") or [])
    ign = set(int(k) for k in (USERDATA.get("rgIgnoredApps") or {}).keys())
    seg_ud = set(USERDATA.get("rgFollowedApps") or [])
    item("4 Seguidos (GetGamesFollowed)", ok=not erro and bool(seg_ids or seg_ud), s=seg, erro=erro,
         seguidos=len(seg_ids), seguidos_na_lista=len(set(seg_ids) & wl),
         seguidos_userdata=len(seg_ud), batem_com_userdata=set(seg_ids) == seg_ud)
    item("4 Ignorados (userdata)", ignorados=len(ign), ignorados_na_lista=len(ign & wl))
    log("   seguidos %d (na lista: %d); ignorados %d (na lista: %d)" % (len(seg_ids), len(set(seg_ids) & wl), len(ign), len(ign & wl)))


# ------------------------------------------------------------------ 5. familia
def familia():
    r, eres, seg, erro = chamar("IFamilyGroupsService", "GetFamilyGroupForUser",
                                {"steamid": S.steamid, "include_family_group_response": True}, token=S.access)
    if erro:
        item("5 Familia", ok=False, s=seg, erro=erro)
        return
    if r.get("is_not_member_of_any_group") or not r.get("family_groupid"):
        item("5 Familia", ok=True, tem_familia=False, s=seg, nota="a conta nao esta em familia")
        log("   sem familia")
        return
    gid = r["family_groupid"]
    membros = len(((r.get("family_group") or {}).get("members")) or [])
    r2, eres2, seg2, erro2 = chamar("IFamilyGroupsService", "GetSharedLibraryApps",
                                    {"family_groupid": gid, "include_own": True, "include_non_games": False,
                                     "steamid": S.steamid}, token=S.access)
    apps = (r2 or {}).get("apps") or []
    wl = set(RES.get("_wl") or [])
    ids = {a["appid"] for a in apps}
    meus = {a["appid"] for a in apps if S.steamid in [str(o) for o in a.get("owner_steamids", [])]}
    item("5 Familia", ok=not erro2, tem_familia=True, membros=membros, jogos_compartilhados=len(apps),
         jogos_so_de_outros=len(ids - meus), lista_na_biblioteca_familia=len(wl & ids),
         lista_so_nos_outros=len((wl & ids) - meus), s_grupo=seg, s_biblioteca=seg2, erro=erro2)
    log("   familia: %d membros, %d jogos (%d so de outros); da lista de desejos, %d ja estao na familia" % (
        membros, len(apps), len(ids - meus), len(wl & ids)))


# ------------------------------------------------------------------ 6. sair
def sair():
    enum = tokens_enumerar()
    n0 = len((enum or {}).get("refresh_tokens") or [])
    meu = [t for t in (enum or {}).get("refresh_tokens", []) if t.get("token_id") == (enum or {}).get("requesting_token")]
    # descricao so do nosso (plataforma/ultimo uso), sem IP
    item("6 Sair: antes", sessoes_listadas=n0, minha_sessao_listada=bool(meu),
         minha_descricao=(meu[0].get("token_description") if meu else None),
         plataforma=(meu[0].get("platform_type") if meu else None))
    r, eres, seg, erro = chamar("IAuthenticationService", "RevokeToken", {"token": S.refresh, "revoke_action": 1}, post=True)
    ok_renova = renovar_apos_revogar()
    enum2 = tokens_enumerar()
    meu2 = [t for t in (enum2 or {}).get("refresh_tokens", []) if t.get("token_id") == (enum or {}).get("requesting_token")]
    item("6 Sair", ok=not erro and not ok_renova, endpoint="IAuthenticationService/RevokeToken {token: refresh, revoke_action: 1}",
         s=seg, erro=erro, eresult=eres, renovacao_depois_falha=not ok_renova,
         sessao_some_da_enumeracao=not meu2, enumeracao_depois_ok=enum2 is not None,
         dispositivos_autorizados="confirmar na conta Steam (Seguranca > Dispositivos autorizados)")
    log("   revogado; renovar depois falha: %s; sessao ainda listada: %s" % (not ok_renova, bool(meu2)))


def renovar_apos_revogar():
    r, eres, seg, erro = chamar("IAuthenticationService", "GenerateAccessTokenForApp",
                                {"refresh_token": S.refresh, "steamid": S.steamid}, post=True)
    return bool(not erro and (r or {}).get("access_token"))


# ------------------------------------------------------------------ celular
def celular():
    r, seg, erro = iniciar_qr(2, "Kurokami Radar (teste celular)")
    if not r:
        raise RuntimeError(erro)
    url = r["challenge_url"]
    print("\n>>> No CELULAR, abra este link no navegador (nao escaneie): %s" % url)
    print(">>> Se ele abrir o app da Steam pedindo para aprovar, aprove. Espero 3 minutos.", flush=True)
    p = aguardar(r)
    item("1 Celular (abrir o link do desafio no proprio celular)", aprovou=bool(p), url_formato=re.sub(r"\d+", "N", url))
    if p:
        S.refresh, S.access = p["refresh_token"], p.get("access_token")
        SEGREDOS.update([S.refresh, S.access])
        S.steamid = jwt(S.refresh)["sub"]
        log("   aprovou pelo link")
        sair()
    else:
        log("   nao aprovou")


ANTES_PACOTES = [205941, 251489, 458885]          # carrinho do dono antes do primeiro teste (ids, nao sao segredo)
ANTES_BUNDLES = [231, 233, 8017, 23487, 34010, 65243]


class _SemRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def diagnostico():
    """Le o carrinho (so ids), compara com o de antes, tira o que o teste deixou e retesta o que falhou."""
    itens, s0, erro = get_cart()
    for i in itens or []:
        log("   item:", {k: i.get(k) for k in ("line_item_id", "packageid", "bundleid", "type", "time_added", "is_valid")})
    k_atual = set(chaves(itens or []))
    k_antes = {(p, 0) for p in ANTES_PACOTES} | {(0, b) for b in ANTES_BUNDLES}
    sobrando, faltando = sorted(k_atual - k_antes), sorted(k_antes - k_atual)
    item("D1 Carrinho agora", itens=len(itens or []), sobrando=sobrando, faltando=faltando, erro=erro)
    log("   sobrando:", sobrando, "faltando:", faltando)
    for i in itens or []:
        if (i.get("packageid") or 0, i.get("bundleid") or 0) in sobrando:
            r, eres, seg, erro = chamar("IAccountCartService", "RemoveItemFromCart",
                                        {"line_item_id": i["line_item_id"], "user_country": PAIS}, post=True, token=S.access)
            log("   remover", i.get("packageid") or i.get("bundleid"), "-> eresult", eres, erro or "")
    itens, _, _ = get_cart()
    k2 = set(chaves(itens or []))
    item("D1 Carrinho depois da limpeza", sobrando=sorted(k2 - k_antes), faltando=sorted(k_antes - k2), itens=len(itens or []))
    log("   depois: sobrando", sorted(k2 - k_antes), "faltando", sorted(k_antes - k2))
    # userdata: guarda o Location do 302
    ck = "steamLoginSecure=%s%%7C%%7C%s" % (S.steamid, S.access)
    for nome, url in (("userdata", LOJA + "dynamicstore/userdata/"),):
        RITMO.aguardar()
        op = urllib.request.build_opener(_SemRedirect)
        try:
            with op.open(urllib.request.Request(url, headers={"Cookie": ck, "User-Agent": rede.UA}), timeout=30) as r:
                corpo = json.loads(r.read().decode("utf-8", "replace"))
            item("D2 userdata", ok=True, seguidos=len(corpo.get("rgFollowedApps") or []), ignorados=len(corpo.get("rgIgnoredApps") or {}),
                 na_lista=len(corpo.get("rgWishlist") or []), no_carrinho=corpo.get("rgAppsInCart"))
            log("   userdata ok: seguidos", len(corpo.get("rgFollowedApps") or []), "ignorados", len(corpo.get("rgIgnoredApps") or {}))
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            item("D2 userdata", ok=False, status=e.code, location=re.sub(r"\d{6,}", "N", loc or ""))
            log("   userdata HTTP", e.code, "Location:", loc)
    # renovacao pelo jeito da loja (cookie de refresh em login.steampowered.com)
    RITMO.aguardar()
    try:
        op = urllib.request.build_opener(_SemRedirect)
        req = urllib.request.Request("https://login.steampowered.com/jwt/refresh?redir=https%3A%2F%2Fstore.steampowered.com%2F",
                                     headers={"Cookie": "steamRefresh_steam=%s%%7C%%7C%s" % (S.steamid, S.refresh), "User-Agent": rede.UA})
        try:
            op.open(req, timeout=30)
        except urllib.error.HTTPError as e:
            item("D3 Renovar pela loja (jwt/refresh)", status=e.code, location=bool(e.headers.get("Location")),
                 set_cookie=[c.split("=")[0] for c in e.headers.get_all("Set-Cookie") or []])
            log("   jwt/refresh:", e.code, [c.split("=")[0] for c in e.headers.get_all("Set-Cookie") or []])
    except Exception as e:
        item("D3 Renovar pela loja", erro=str(e))
    # renovacao oficial com renewal_type
    renovar({"renewal_type": 1})
    # lista de desejos: retesta a escrita com resposta bruta
    antes, _, _ = wl_token()
    base = {i["appid"] for i in antes}
    alvo = next(a for a in (570, 230410, 1172470, 553850) if a not in base)
    r, eres, s1, e1 = chamar("IWishlistService", "AddToWishlist", {"appid": alvo}, post=True, token=S.access)
    time.sleep(2)
    meio, _, _ = wl_token()
    entrou = any(i["appid"] == alvo for i in meio)
    chamar("IWishlistService", "RemoveFromWishlist", {"appid": alvo}, post=True, token=S.access)
    dep, _, _ = wl_token()
    item("D4 Lista: escrita (retestada)", appid=alvo, resposta_add=r, eresult_add=eres, entrou=entrou,
         antes=len(antes), meio=len(meio), depois=len(dep), igual={i["appid"] for i in dep} == base)
    log("   wishlist add %s: resposta=%s eresult=%s entrou=%s antes/meio/depois=%d/%d/%d" % (alvo, r, eres, entrou, len(antes), len(meio), len(dep)))
    r, eres, seg, erro = chamar("IStoreService", "GetGamesFollowedCount", {"steamid": S.steamid}, token=S.access)
    item("D5 Seguidos (contagem)", resposta=r, s=seg, erro=erro)
    log("   seguidos (contagem):", r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--celular", action="store_true")
    ap.add_argument("--diag", action="store_true")
    a = ap.parse_args()
    try:
        if a.celular:
            passo("Celular", celular)
            return
        if a.diag:
            passo("1 Login por QR", login)
            if S.refresh:
                passo("D Diagnostico", diagnostico)
            return
        passo("1 Login por QR", login)
        if not S.refresh:
            return
        passo("1b Renovar", lambda: renovar())
        passo("4a userdata", ler_userdata)
        passo("3a Lista: leitura", lista_leitura)
        passo("2 Carrinho", carrinho)
        passo("3b Lista: escrita", lista_escrita)
        passo("4 Seguidos e ignorados", seguidos)
        passo("5 Familia", familia)
    finally:
        if S.refresh and "6 Sair" not in RES["itens"]:
            passo("6 Sair", sair)
        RES.pop("_wl", None)
        salvar()
        log("\nResultado bruto (sem tokens):", SAIDA)


if __name__ == "__main__":
    main()
