"""Agrupa jogos da mesma serie pelo nome, em vez do campo "franquia" da Steam
(que mistura coisas como "EA Play" e separa "Need for Speed" de "Need For Speed")."""
import re

EDICAO = {"remastered", "remaster", "remake", "definitive", "edition", "goty", "complete", "deluxe", "hd", "collection",
          "anniversary", "enhanced", "director", "directors", "cut", "redux", "ultimate", "standard", "gold", "premium",
          "classic", "reloaded", "legendary", "royal", "trilogy", "bundle", "pack", "plus", "dx", "game", "of", "the", "year"}
ROMANOS = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv", "xvi"}
COMUNS = {"the", "a", "an", "o", "os", "as"}


def tokens(nome):
    n = (nome or "").lower().replace("™", "").replace("®", "").replace("©", "").replace("’", "'").replace("'", "")
    n = re.split(r"\s*(?::|\s[-–—]\s)\s*", n)[0]  # tira o subtitulo
    t = re.findall(r"[a-z0-9]+", n)
    while t and t[0] in COMUNS:
        t = t[1:]
    while len(t) > 1 and (t[-1].isdigit() or t[-1] in ROMANOS or t[-1] in EDICAO):
        t = t[:-1]
    return t


LIGACAO = {"of", "for", "the", "de", "and", "da", "do"}


def chave(nome):
    t = tokens(nome)
    if not t:
        return None
    if len(t) >= 3 and t[1] in LIGACAO:
        return " ".join(t[:3])  # "call of duty" != "call of juarez"; "need for speed"
    return " ".join(t[:2]) if len(t) >= 2 else t[0]


def rotulo(nomes):
    """Prefixo comum dos nomes, recortado do primeiro nome original (mantem a grafia: "Half-Life", "Need for Speed")."""
    ts = [tokens(n) for n in nomes]
    comum = []
    for i in range(min(len(t) for t in ts)):
        w = ts[0][i]
        if all(t[i] == w for t in ts):
            comum.append(w)
        else:
            break
    if not comum:
        return nomes[0]
    orig = re.split(r"\s*(?::|\s[-–—]\s)\s*", re.sub(r"[™®©]", "", nomes[0]))[0]
    ini = fim = None
    k = 0
    for m in re.finditer(r"[A-Za-z0-9'’]+", orig):
        w = re.sub(r"['’]", "", m.group(0)).lower()
        if k == 0 and w != comum[0]:
            continue  # "The" do comeco, quando a serie nao comeca com ele
        if w != comum[k]:
            break
        ini = m.start() if ini is None else ini
        fim = m.end()
        k += 1
        if k == len(comum):
            break
    return orig[ini:fim].strip() if ini is not None else " ".join(comum).title()


def agrupar(itens):
    """itens: [{"appid", "nome", ...}] -> {chave: [itens]}"""
    grupos = {}
    for it in itens:
        k = chave(it.get("nome"))
        if k:
            grupos.setdefault(k, []).append(it)
    return grupos
