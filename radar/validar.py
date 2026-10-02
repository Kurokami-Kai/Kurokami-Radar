"""Testa cada chave com uma chamada real e explica o resultado."""
import re
import urllib.error
import urllib.parse

from .rede import explicar, http_json

DICAS = {
    "steam": "Opcional: so serve para ler a biblioteca quando nao ha userdata.json. Use a 'Key' de steamcommunity.com/dev/apikey (32 caracteres, 0-9 e A-F). "
             "Se voce gerou uma chave nova, a antiga parou de funcionar.",
    "itad": "Em isthereanydeal.com/apps/my, registre um app (qualquer nome) e copie o campo 'API Key' - "
            "nao o 'OAuth Client ID' nem o 'Client Secret'.",
    "ggdeals": "Em gg.deals/settings, secao Connections, copie a 'GG.deals API key' (precisa confirmar o e-mail da conta).",
}


def formato_suspeito(nome, chave):
    if not chave:
        return "vazia"
    if re.search(r"[\x00-\x1f\s]", chave):
        return "tem espacos ou caracteres de controle (colagem falhou?)"
    if nome == "steam" and not re.fullmatch(r"[0-9A-Fa-f]{32}", chave):
        return "a chave da Steam tem 32 caracteres hexadecimais; esta tem %d" % len(chave)
    return None


def testar(nome, chave):
    """(ok, mensagem)"""
    if not chave:
        return None, "nao cadastrada"
    suspeita = formato_suspeito(nome, chave)
    try:
        if nome == "steam":
            http_json("https://api.steampowered.com/ISteamWebAPIUtil/GetSupportedAPIList/v1/?key=" + urllib.parse.quote(chave))
        elif nome == "itad":
            http_json("https://api.isthereanydeal.com/lookup/id/shop/61/v1?key=" + urllib.parse.quote(chave), corpo=["app/10"])
        elif nome == "ggdeals":
            r = http_json("https://api.gg.deals/v1/prices/by-steam-app-id/?" +
                          urllib.parse.urlencode({"ids": "10", "key": chave, "region": "br"}))
            if isinstance(r, dict) and r.get("success") is False:
                return False, "recusada: %s" % (r.get("data") or r)
        return True, "ok"
    except urllib.error.HTTPError as e:
        msg = "recusada (%s)" % explicar(e)
        if suspeita:
            msg += " - formato: " + suspeita
        return False, msg
    except Exception as e:
        return False, "sem resposta (%s) - problema de rede, nao necessariamente da chave" % e


def testar_perfil(perfil):
    """(ok, mensagem, steamid). Usa so dados publicos: nao precisa de chave."""
    from . import steam
    perfil = (perfil or "").strip()
    if not perfil:
        return False, "informe o link do seu perfil", None
    try:
        sid = steam.resolver_steamid(None, perfil)
    except Exception as e:
        return False, "perfil nao encontrado (%s)" % e, None
    try:
        n = len(steam.wishlist(None, sid))
    except Exception as e:
        return False, "nao consegui ler a lista de desejos (%s)" % explicar(e), sid
    if n == 0:
        return False, ("a lista de desejos veio vazia: ela esta privada? Na Steam: Perfil > Editar perfil > "
                       "Privacidade > Detalhes dos jogos = Publico"), sid
    return True, "ok: %d itens na lista de desejos" % n, sid
