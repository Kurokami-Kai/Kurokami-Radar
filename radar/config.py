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
        # Raridade minima para avisar: comum, incomum, raro, ultrarraro, lendario.
        # Mede quanto tempo o jogo ja passou nesse preco (ou menos) no historico das lojas que alertam.
        "raridade_minima": "raro",
        # (informativo) piso por janela: 90 (3 meses), 180, 270, 365 (1 ano) ou 0 (so o de todos os tempos).
        # Cada jogo ganha a etiqueta do maior piso que atinge (sempre > 1 ano > 9m > 6m > 3m).
        "janela_dias": 90,
        # "Perto do menor de sempre": vale mesmo sem bater piso nenhum se a diferenca for pequena
        # em relacao ao preco cheio (HL Miami 2: R$ 7,04 x R$ 4,99 num jogo de R$ 46,99 = 4% do cheio).
        "perto": {"ativo": True, "pct_do_cheio": 10, "reais": 3},
        "score_minimo": 60,           # 0 a 100 (desconto x qualidade das analises)
        "desconto_minimo": 50,
        "avaliacao_minima": 75,       # % de analises positivas
        "ignorar_sem_avaliacoes": True,
        "dias_minimos_completo": 14,  # modo completo: so alerta depois de observar o custo por esse tempo
        # os N primeiros da sua lista de desejos (ordem que voce deu na Steam) so precisam bater o piso:
        # score, desconto e avaliacao minimos nao valem para eles
        "favoritos_top": 10
    },

    "notificacoes": {
        "ativas": True,
        "max_por_rodada": 5,            # acima disso, os demais viram uma notificacao-resumo
        "melhora_minima_reais": 0.5,    # jogo ja avisado so avisa de novo se cair pelo menos isso
        "silencio": {"ativo": False, "de": "23:00", "ate": "08:00"},
        "termina_em_breve_horas": 24    # avisa quando algo do carrinho/"vale a pena" esta acabando (0 desliga)
    },

    "keyshops": {
        "ativo": True,
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

    "intervalos_minutos": {"itad": 30, "ggdeals": 60, "steam": 180},
    # verificacao completa (tudo, sem limite de ritmo): a 1a sempre; depois a cada N dias (0 = so manual)
    "verificacao_completa_dias": 7,
    # A loja da Steam so responde ~200 chamadas a cada 5 min. O que depende dela (conteudo de edicoes,
    # lista de DLCs) vai sendo completado aos poucos, sem atrasar a checagem de precos.
    "chamadas_lentas_por_rodada": 120,
    "historico": {"importar_dias": 1825}
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
    else:
        salvar(cfg)
        print("Criei o config.json com os valores padrao.")
    return cfg


def salvar(cfg):
    with open(caminhos.ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def modo_do_jogo(cfg, appid):
    return (cfg.get("completo") or {}).get("jogos", {}).get(str(appid)) or cfg["completo"].get("padrao", "base")
