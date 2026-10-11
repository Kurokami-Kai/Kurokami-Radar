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
    "item": "Item, arma ou armadura",
}

_R = lambda s: re.compile(s, re.I)
REGRAS = [
    ("extra", _R(r"sound ?track|\bost\b|trilha sonora|art ?book|digital art|wallpaper|papel de parede|making of|"
                 r"\bcomic|quadrinho|strategy guide|edition extras|deluxe extras|\bbonus content\b|guia (digital|de estrat)|novel\b|mini ?book|livro de arte|"
                 r"sound collection|piano collection|extra tracks|\bbgm\b|original (score|album)|\bmusic\b|\balbum\b")),
    ("cosmetico", _R(r"\bskins?\b|costume|outfit|cosmetic|cosm[eé]tic|traje|roupa|apar[eê]ncia|livery|paint ?job|"
                     r"pintura|decal|sticker|adesiv|emote|avatar|\bhats?\b|chap[eé]u|hair ?style|penteado|camo\b|camufla|"
                     r"attire|uniform|swimsuit|\bcolor pack|\bcolou?rs?\b pack|portrait|moldura|\bframes?\b|"
                     r"\btheme\b|\btema\b|weapon (skin|charm)|\bcharms?\b|visual pack|appearance|look pack|cosmetics|"
                     r"maquiagem|makeup|\bgestures?\b|\bposes?\b|\bemblems?\b|\bbanners?\b|\bnameplate|\bhorn\b|\bmasks?\b|"
                     r"m[aá]scara|\bdyes?\b|\bvoice pack|\bpacote de voz|\bnarrator|\bannouncer")),
    ("atalho", _R(r"time ?saver|booster|\bboost|currency|\d+\s*\w*\s*(coins?|gems?|moedas?)\b|coin pack|\bcredits? pack|"
                  r"\bxp\b|experience pack|starter (pack|kit)|pacote inicial|unlock(s| all| pack)|desbloque|"
                  r"resource pack|recursos|shortcut|atalho|premium currency|gold pack|\bpoints\b|"
                  r"\d[\d.,]*\s*(\w+\s+)?(orbs?|souls|crystals?|cash|gold|ouro|pontos|points|credits|cr[eé]ditos)\b")),
    ("pacote", _R(r"\bupgrade\b|deluxe|ultimate edition|complete edition|gold edition|definitive edition|"
                  r"edi[cç][aã]o (deluxe|completa|definitiva|ouro)|\bbundle\b|\bcollection\b|cole[cç][aã]o")),
    ("historia", _R(r"expans|expansion|season pass|passe de temporada|year \d pass|epis[oó]dio|episode|chapter|"
                    r"cap[ií]tulo|campaign|campanha|\bstory\b|hist[oó]ria|missions?\b|miss(ão|ões|ao|oes)|"
                    r"\bact [ivx\d]|\bato [ivx\d]|\bpart \d|parte \d")),
    ("item", _R(r"\bweapons?\b|\barmou?r|armadura|\barmas?\b|pingente|pendant|\bgear\b|equipment|equipamento|"
                r"\bsniper pack|\bgun pack|\bmask pack|\bloadout|ingredient|\bpowder\b|\bmaterials?\b|\bfood\b|consum[ií]ve|"
                r"\bitem (set|pack|bundle)s?\b|\bconj(unto|\.)? de|\bset \d+\b|\bsepith\b|g-pom|droplet|\bpe[cç]a de|\bpe[cç]a\b|"
                r"\bkits?\b|\brecipes?\b|\breceitas?\b|\bpacote de (itens|armas)|\bsets?( [a-z]| ?\d+| vol\.? ?\d+)?\s*$")),
]


def _sem_titulo(nome, pai):
    """Tira o nome do jogo do comeco do da DLC ("Trails in the Sky 1st Chapter - Zeram Powder" -> "Zeram Powder"):
    palavras do titulo (Chapter, Part, Collection...) enganavam as regras."""
    if pai and nome.lower().startswith(pai.lower()):
        resto = nome[len(pai):].lstrip(" -–—:|").strip()
        if resto:
            return resto
    return nome


def classificar(nome, pai=None):
    nome = _sem_titulo(nome or "", pai)
    for classe, rx in REGRAS:
        if rx.search(nome):
            return classe
    return "conteudo"


def ignorada(classe, preco, cfg_dlc, tenho=False):
    """True se a DLC nao conta (custo completo, "falta", totais). tenho=True: DLC que voce ja tem, de preco as vezes
    desconhecido (sem preco nao e "gratis": so as regras por classe valem)."""
    if cfg_dlc.get("ignorar_cosmeticos") and classe == "cosmetico":
        return True
    if cfg_dlc.get("ignorar_extras") and classe == "extra":
        return True
    if cfg_dlc.get("ignorar_atalhos") and classe == "atalho":
        return True
    if cfg_dlc.get("ignorar_pacotes") and classe == "pacote":
        return True
    if cfg_dlc.get("ignorar_itens", True) and classe == "item":
        return True
    if cfg_dlc.get("so_expansoes") and classe not in ("historia", "pacote"):
        return True
    if tenho and preco is None:
        return False
    if cfg_dlc.get("ignorar_gratis", True) and (preco or 0) == 0:
        return True
    minimo = cfg_dlc.get("preco_minimo") or 0
    if minimo and preco is not None and preco < minimo * 100:
        return True
    return False
