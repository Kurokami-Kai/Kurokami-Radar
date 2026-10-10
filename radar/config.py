"""config.json: tudo que nao e segredo. O painel web (etapa 3) vai editar este arquivo."""
import copy
import json
import os

from . import caminhos

PADRAO = {
    "perfil_steam": "",           # link do perfil, nome personalizado ou SteamID64 (pedido na primeira vez)
    "pais": "BR",
    "userdata_json": "",
    "pasta_kurokami_precos": "",

    # Lojas oficiais monitoradas (nomes como aparecem na IsThereAnyDeal; veja: py radar.py lojas)
    "lojas": ["Steam", "GreenManGaming", "Nuuvem", "Hype Games", "2Game"],
    "somente_drm_steam": True,

    "alerta": {
        # menor_historico: so dispara no piso (com tolerancia) das lojas marcadas
        "modo": "menor_historico",
        "tolerancia_pct": 0,          # 5 = aceita ate 5% acima do menor historico
        # O que avisa (0.15, spec 04): tipos de preco em reais nas lojas marcadas.
        #   selo  = Selo Kurokami: o menor preco em muito tempo (recorde anterior de 1,5 ano ou mais, ou preco pela metade)
        #   novo  = novo recorde (nunca esteve tao barato) · igual = igual ao recorde · 24m = menor preco em 2 anos
        # O Selo avisa a partir de selo_corte_minimo; os outros, a partir de desconto_minimo.
        "tipos": {"selo": True, "novo": False, "igual": False, "24m": False},
        "raridade_minima": "raro",    # (ignorado desde a 0.15: a raridade so informa, na coluna "Costuma voltar")
        "selo_corte_minimo": 0,       # so ganha Selo a partir deste corte (%)
        # (informativo) piso por janela: 90 (3 meses), 180, 270, 365 (1 ano) ou 0 (so o de todos os tempos).
        # Cada jogo ganha a etiqueta do maior piso que atinge (sempre > 1 ano > 9m > 6m > 3m).
        "janela_dias": 90,
        # "Perto do menor de sempre": vale mesmo sem bater piso nenhum se a diferenca for pequena
        # em relacao ao preco cheio (HL Miami 2: R$ 7,04 x R$ 4,99 num jogo de R$ 46,99 = 4% do cheio).
        "perto": {"ativo": True, "pct_do_cheio": 10, "reais": 3},
        "desconto_minimo": 50,
        # (ignorados desde a 0.14: analises nao decidem mais alertas; ficam por compatibilidade)
        "score_minimo": 60,
        "avaliacao_minima": 75,
        "ignorar_sem_avaliacoes": True,
        "dias_minimos_completo": 14,  # modo completo: so alerta depois de observar o custo por esse tempo
        # (ignorado desde a 0.15: favoritos nao tem mais excecao de aviso; fica por compatibilidade)
        "favoritos_top": 10
    },

    "notificacoes": {
        "ativas": True,
        "max_por_rodada": 5,            # acima disso, os demais viram uma notificacao-resumo
        "melhora_minima_reais": 0.5,    # jogo ja avisado so avisa de novo se cair pelo menos isso
        "silencio": {"ativo": False, "de": "23:00", "ate": "08:00"},
        "termina_em_breve_horas": 24,   # avisa quando algo do carrinho/"vale a pena" esta acabando (0 desliga)
        # Telegram: o mesmo aviso no celular (bot gratuito; o token fica no keyring, o chat_id aqui)
        "telegram": {"ativo": False, "chat_id": ""}
    },

    "keyshops": {
        # desligado por padrao (07/10/2026): 22 dos 26 avisos reais eram keyshop da GG.deals, quase todos
        # alarme falso (classicos da Valve a R$ 7-9 de novo a cada centavo). O preco segue no painel.
        "ativo": False,
        # keyshop so entra quando o preco e MUITO baixo:
        # abaixo de preco_maximo  OU  abaixo de X% do menor preco oficial.
        "preco_maximo": 10.0,
        "pct_do_menor_oficial": 50
    },

    "dlc": {
        "ignorar_cosmeticos": True,
        "ignorar_extras": True,       # trilha sonora, artbook, wallpaper...
        "ignorar_atalhos": True,      # boosters, moedas, time savers
        "ignorar_pacotes": False,     # DLCs que juntam outras (ex.: HITMAN "Deluxe Pack") - contam por padrao
        "ignorar_gratis": True
    },

    # "base": avalia o jogo sozinho; "completo": avalia o custo de ter tudo que importa.
    # Por jogo: {"appid": "completo"}. Ex.: {"1659040": "completo"} para o HITMAN World of Assassination.
    "completo": {
        "padrao": "base",
        "jogos": {}
    },

    "bundles": {
        "mostrar_parciais": True,
        "cobertura_minima_pct": 50    # bundle so aparece se cobrir ao menos isso do conteudo relevante
    },

    # de onde vem as versoes novas (GitHub Releases, repositorio publico)
    "atualizacao": {"repo": "Kurokami-Kai/Kurokami-Radar", "verificar": True},

    # rede_local: deixa abrir o painel pelo celular/outro PC da mesma rede (com codigo de acesso)
    "painel": {"rede_local": False},

    # jogos monitorados que nao estao na lista de desejos da Steam (adicionados pelo painel)
    "extras": [],

    # Promocoes da Steam inteira na aba Promocoes (spec 07): ~1 MB por consulta num dia comum, ~16 MB em grande promocao
    "steam_inteira": True,
    # historico (para Selo, Menor em 2 anos, Costuma voltar) de quem esta perto do recorde: N jogos por rodada
    # (a ITAD aceita ~100 chamadas a cada 5 min, e a lista tambem usa)
    "steam_inteira_hist_por_rodada": 60,

    "intervalos_minutos": {"itad": 30, "ggdeals": 60, "steam": 180, "steam_inteira": 60},
    # verificacao completa (tudo, sem limite de ritmo): a 1a sempre; depois a cada N dias (0 = so manual)
    "verificacao_completa_dias": 7,
    # A loja da Steam so responde ~200 chamadas a cada 5 min. O que depende dela (conteudo de edicoes,
    # lista de DLCs) vai sendo completado aos poucos, sem atrasar a checagem de precos.
    "chamadas_lentas_por_rodada": 120,
    "historico": {"importar_dias": 1825},

    # mudancas de padrao ja aplicadas a este config.json (cada uma roda uma vez so; ver _migrar)
    "migracoes": []
}

# nome -> funcao que ajusta um config.json antigo. Depois de rodar, o nome entra em cfg["migracoes"]
# e a escolha do usuario passa a valer (se ele religar, fica ligado).
MIGRACOES = {
    "keyshop_alerta_off": lambda cfg: cfg["keyshops"].update(ativo=False),
}


def _mesclar(base, novo):
    for k, v in novo.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def carregar():
    cfg = copy.deepcopy(PADRAO)
    if os.path.isfile(caminhos.ARQ_CONFIG):
        try:
            with open(caminhos.ARQ_CONFIG, encoding="utf-8-sig") as f:
                _mesclar(cfg, json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            print("!! config.json ilegivel (%s). Usando o padrao." % e)
            return cfg  # nao migra: gravaria o padrao por cima do arquivo do usuario
    else:
        salvar(cfg)
        print("Criei o config.json com os valores padrao.")
    _migrar(cfg)
    return cfg


def _migrar(cfg):
    feitas = cfg.get("migracoes") or []
    novas = [n for n in MIGRACOES if n not in feitas]
    if not novas:
        return
    for n in novas:
        MIGRACOES[n](cfg)
    cfg["migracoes"] = feitas + novas
    try:
        salvar(cfg)
    except OSError as e:
        print("!! nao consegui gravar o config.json (%s)" % e)


def salvar(cfg):
    with open(caminhos.ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def modo_do_jogo(cfg, appid):
    return (cfg.get("completo") or {}).get("jogos", {}).get(str(appid)) or cfg["completo"].get("padrao", "base")
