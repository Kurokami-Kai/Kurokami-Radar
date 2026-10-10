"""Telegram (bot gratuito): espelha os avisos no celular, fora de casa.
O token do bot fica no keyring ("telegram"); o chat_id (nao e segredo) em config.notificacoes.telegram."""
import json
import logging
import time
import urllib.error
import urllib.request
from html import escape

from . import credenciais

API = "https://api.telegram.org/bot%s/%s"
_PAUSA_ATE = 0.0  # depois de uma falha, pula os avisos seguintes por 2 min (sem rede, nao trava o ciclo)


def _chamar(token, metodo, dados=None, timeout=8):
    """Devolve (ok, resposta_json_ou_erro). Nunca levanta: aviso que falha nao pode derrubar a coleta."""
    req = urllib.request.Request(API % (token, metodo), data=json.dumps(dados or {}).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "User-Agent": "KurokamiRadar"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read().decode("utf-8")).get("description") or "erro %d" % e.code
        except Exception:
            return False, "erro %d" % e.code
    except Exception as e:
        return False, str(e) or e.__class__.__name__


def _cfg(cfg):
    return ((cfg.get("notificacoes") or {}).get("telegram")) or {}


def ligado(cfg):
    """Ligado + token + conversa vinculada."""
    t = _cfg(cfg)
    return bool(t.get("ativo") and t.get("chat_id") and credenciais.ler("telegram"))


def enviar(cfg, titulo, texto="", botoes=(), foto=None):
    """botoes: [(rotulo, url)]: so links https publicos (localhost e file:/// nao abrem no celular).
    foto: URL da imagem (a capa); se o Telegram nao conseguir baixar, vai so o texto."""
    global _PAUSA_ATE
    if not ligado(cfg) or time.time() < _PAUSA_ATE:
        return False
    token, chat = credenciais.ler("telegram"), _cfg(cfg)["chat_id"]

    def corpo(n):  # corta ANTES de escapar, para nao partir um "&amp;" ao meio
        c = "<b>%s</b>" % escape(str(titulo)[:200])
        return c + ("\n" + escape(str(texto)[:n]) if texto else "")

    teclado = [[{"text": r[:60], "url": u}] for r, u in list(botoes)[:5] if str(u).startswith("https://")]
    extra = {"reply_markup": {"inline_keyboard": teclado}} if teclado else {}
    if foto:
        ok, _ = _chamar(token, "sendPhoto", dict(chat_id=chat, photo=foto, caption=corpo(700), parse_mode="HTML", **extra))
        if ok:
            return True
    ok, r = _chamar(token, "sendMessage", dict(chat_id=chat, text=corpo(3500), parse_mode="HTML",
                                              disable_web_page_preview=True, **extra))
    if not ok:
        _PAUSA_ATE = time.time() + 120
        logging.getLogger("radar").warning("Telegram: %s", r)
    return ok


def conectar(token):
    """Testa o token (getMe). Devolve (ok, @usuario_do_bot ou mensagem de erro)."""
    ok, r = _chamar(token, "getMe")
    if not ok:
        return False, "token recusado pelo Telegram (%s)" % r
    return True, "@" + (r.get("result") or {}).get("username", "")


def achar_conversa(token):
    """Chat de quem mandou mensagem ao bot. Devolve (chat_id, nome) ou (None, motivo)."""
    ok, r = _chamar(token, "getUpdates", {"limit": 50})
    if not ok:
        return None, r
    chats = {}
    for u in r.get("result") or []:
        c = (u.get("message") or {}).get("chat") or {}
        if c.get("type") == "private" and c.get("id"):
            chats[c["id"]] = c.get("first_name") or c.get("username") or "você"
    if len(chats) > 1:  # o @ do bot e publico: outra pessoa pode ter escrito antes de voce
        return None, "mais de uma pessoa escreveu ao bot (%s); crie outro bot só seu" % ", ".join(chats.values())
    for i, nome in chats.items():
        return i, nome
    return None, "nenhuma mensagem ao bot ainda"
