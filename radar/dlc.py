"""Classificacao automatica de DLCs pelo nome (pt/en). O painel vai permitir
corrigir item a item; correcoes do usuario nunca sao sobrescritas."""
import re

CLASSES = {
    "historia": "História / expansão",
    "conteudo": "Conteúdo jogável",
    "cosmetico": "Cosmético",
    "atalho": "Atalho / moeda",
    "extra": "Extra (trilha, artbook)",
    "pacote": "Pacote / upgrade de edição",
}

_R = lambda s: re.compile(s, re.I)
REGRAS = [
    ("extra", _R(r"sound ?track|\bost\b|trilha sonora|art ?book|digital art|wallpaper|papel de parede|making of|"
                 r"\bcomic|quadrinho|strategy guide|edition extras|deluxe extras|\bbonus content\b|guia (digital|de estrat)|novel\b|mini ?book|livro de arte")),
    ("cosmetico", _R(r"\bskins?\b|costume|outfit|cosmetic|cosm[eé]tic|traje|roupa|apar[eê]ncia|livery|paint ?job|"
                     r"pintura|decal|sticker|emote|avatar|\bhats?\b|chap[eé]u|hair ?style|penteado|camo\b|camufla|"
                     r"attire|uniform|swimsuit|\bcolor pack|\bcolou?rs?\b pack|portrait|moldura|\bframes?\b|"
                     r"\btheme\b|\btema\b|weapon (skin|charm)|\bcharms?\b|visual pack|appearance|look pack|cosmetics")),
    ("atalho", _R(r"time ?saver|booster|\bboost|currency|\d+\s*\w*\s*(coins?|gems?|moedas?)\b|coin pack|\bcredits? pack|"
                  r"\bxp\b|experience pack|starter (pack|kit)|pacote inicial|unlock(s| all| pack)|desbloque|"
                  r"resource pack|recursos|shortcut|atalho|premium currency|gold pack|\bpoints\b")),
    ("pacote", _R(r"\bupgrade\b|deluxe|ultimate edition|complete edition|gold edition|definitive edition|"
                  r"edi[cç][aã]o (deluxe|completa|definitiva|ouro)|\bbundle\b|\bcollection\b|cole[cç][aã]o")),
    ("historia", _R(r"expans|expansion|season pass|passe de temporada|year \d pass|epis[oó]dio|episode|chapter|"
                    r"cap[ií]tulo|campaign|campanha|\bstory\b|hist[oó]ria|missions?\b|miss(ão|ões|ao|oes)|"
                    r"\bact [ivx\d]|\bato [ivx\d]|\bpart \d|parte \d")),
]


def classificar(nome):
    nome = nome or ""
    for classe, rx in REGRAS:
        if rx.search(nome):
            return classe
    return "conteudo"


def ignorada(classe, preco, cfg_dlc):
    if cfg_dlc.get("ignorar_cosmeticos") and classe == "cosmetico":
        return True
    if cfg_dlc.get("ignorar_extras") and classe == "extra":
        return True
    if cfg_dlc.get("ignorar_atalhos") and classe == "atalho":
        return True
    if cfg_dlc.get("ignorar_pacotes") and classe == "pacote":
        return True
    if cfg_dlc.get("ignorar_gratis", True) and (preco or 0) == 0:
        return True
    return False
