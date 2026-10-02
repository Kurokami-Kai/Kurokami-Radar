"""Chaves de API no Gerenciador de Credenciais do Windows (via keyring).
Nada de chave em arquivo: o config.json pode ser compartilhado sem risco."""
import getpass
import os

SERVICO = "Kurokami Radar"
CHAVES = {
    "steam": ("Steam Web API", "https://steamcommunity.com/dev/apikey", False),
    "itad": ("IsThereAnyDeal", "https://isthereanydeal.com/apps/my/", True),
    "ggdeals": ("GG.deals", "https://gg.deals/settings/ (Connections)", False),
}

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # sem keyring: so variaveis de ambiente
    keyring = None
    KeyringError = Exception


def disponivel():
    return keyring is not None


def ler(nome):
    env = os.environ.get("KUROKAMI_%s_KEY" % nome.upper())
    if env:
        return env.strip()
    if keyring is None:
        return None
    try:
        v = keyring.get_password(SERVICO, nome)
        return v.strip() if v else None
    except KeyringError:
        return None


def gravar(nome, valor):
    if keyring is None:
        raise RuntimeError("Instale o keyring: py -m pip install keyring")
    if valor:
        keyring.set_password(SERVICO, nome, valor.strip())
    else:
        try:
            keyring.delete_password(SERVICO, nome)
        except Exception:
            pass


def mascarar(v):
    return "(vazia)" if not v else "%s…%s (%d caracteres)" % (v[:4], v[-3:], len(v))


def limpar(v):
    """Chaves sao ASCII visivel: tira espacos, aspas e qualquer caractere de controle
    (Ctrl+V que nao colou vira um caractere invisivel)."""
    import re
    v = re.sub(r"[^\x21-\x7e]", "", v or "")
    return v.strip("\"'")


def configurar_interativo(so_faltando=False):
    """Pergunta as chaves no terminal e testa cada uma na hora. Enter mantem a atual."""
    from .validar import DICAS, testar
    if keyring is None:
        print("!! O pacote 'keyring' nao esta instalado. Rode: py -m pip install keyring")
        return False
    print("As chaves ficam no Gerenciador de Credenciais do Windows, em '%s'." % SERVICO)
    print("Enter mantem a atual. Digite - para apagar. Para colar, clique com o botao direito.\n")
    for nome, (titulo, onde, obrig) in CHAVES.items():
        atual = ler(nome)
        if so_faltando and atual:
            continue
        for tentativa in range(3):
            print("%s %s  [atual: %s]" % (titulo, "(obrigatoria)" if obrig else "(opcional)", mascarar(atual)))
            print("   gere em: %s" % onde)
            bruto = input("   chave (fica visivel; feche a janela depois): ")
            if bruto.strip() == "-":
                gravar(nome, None)
                print("   apagada.\n")
                break
            novo = limpar(bruto)
            if not novo:
                print("   mantida.\n")
                break
            print("   recebi %s" % mascarar(novo))
            ok, msg = testar(nome, novo)
            if ok or ok is None:
                gravar(nome, novo)
                print("   testada e salva.\n")
                break
            print("   !! %s" % msg)
            print("   dica: %s" % DICAS[nome])
            if "sem resposta" in msg:
                gravar(nome, novo)
                print("   salvei mesmo assim; teste depois com: py radar.py testar\n")
                break
            print("   nao salvei. Tente de novo (Enter para pular).\n")
            atual = ler(nome)
    return True


def faltando_obrigatorias():
    return [CHAVES[n][0] for n, (_, _, ob) in CHAVES.items() if ob and not ler(n)]
