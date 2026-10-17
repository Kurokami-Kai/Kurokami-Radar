# Pendências e ideias

## Especificações prontas para implementar
- [09 — Biblioteca nova](specs/09-biblioteca-nova.md): **feita** (Etapas 1 e 2 e Ofertas, em v0.17.0); **falta só a Etapa 3** (ver a franquia inteira, em discussão); absorve a 03
- **Previsão pelo histórico de cada usuário** (a previsão já funciona, em `radar/previsao.py`): falta só recalcular. `previsao.TABELA` é o backtest do dono (699 jogos); rodar o backtest no Hunter de tempos em tempos (ex.: uma vez por semana, depois da coleta) e usar a tabela de cada um. Medir antes quanto tempo leva numa lista de 700 jogos.
- **Ofertas e Biblioteca no celular:** o topo do painel ocupa ~320 px numa tela de 375 px; recolher o topo (ou só o ícone e o menu) quando a página nova está aberta.
- [10 — App para o celular (APK)](specs/10-app-celular.md): **em discussão** (opções A–E; o PC do dono não fica ligado o dia todo; recomendação provisória: Telegram + PWA/APK "casca" com Tailscale)
- [03 — Franquias com capas, cinza e recolher/expandir](specs/03-franquias-com-capas.md) (entra na 09)
- 05 — Veredito na ficha, keyshop decente e limpeza das Configurações (a escrever)
- [07 — Promoções da Steam inteira](specs/07-steam-inteira.md): feito em v0.17.0 (revisada em 08/10 com recordes e histórico também fora da lista, menus no topo, sem botão de fonte). Ideia original: Sem login nem perfil público, Promoções mostra a Steam inteira (como a SteamDB) e os filtros pessoais (lista de desejos, seguidos, família, carrinho) aparecem bloqueados com "Entre com a Steam para usar".
- 08 — Layout em etapas: inventário, referência, base visual, uma aba por vez, celular (a escrever)

## Feitas
- **Abertura animada do painel** (v0.17.2) e **Telegram** (v0.18.0: avisos de oferta, guia em Configurações → Telegram).
- **Painel dividido** (v0.17.2): `painel.html` só com o HTML; CSS e JS em `radar/painel-web/`, juntados pelo servidor. Falta, se valer a pena, o mesmo em `ofertas.html` (~120 KB) e `biblioteca.html`.
- [06 — Login Steam: "Entrar pela Steam" (OpenID) feito em v0.16.0; o QR foi descartado e o carrinho vai pela extensão do Hunter](specs/06-login-steam.md)
- [04 — Vitrine, aba Promoções e avisos por tipo de recorde (feito em v0.15.0)](specs/04-vitrine-promocoes-e-avisos.md)
- [01 — Raridade v2, Selo Kurokami e fim da avaliação como métrica (feito em v0.14.0)](specs/01-selo-kurokami-e-raridade.md)
- [02 — DLCs não aparecem (feito em v0.13.0)](specs/02-dlcs-nao-aparecem.md)

## Ideias

Em ordem aproximada de valor. Nada aqui foi iniciado.

- **Desempenho (pedido do dono, 17/10: "péssimo; até no meu PC a verificação demora demais"). Medido em 17/10 (`radar.log` de 2–17/10, 511 ciclos, e cópia do banco instalado de 571 MB, `promo_hist` com 3,5 mi de linhas):** a pista rápida leva mediana 56 s (p90 112 s): Steam inteira ~48 s (28 s de rede + ~20 s de recordes da ITAD e `steam_inteira.avaliar`), preços da ITAD 5 s, GG.deals 9 s (a cada 2 ciclos), `analise.avaliar` 10–14 s; 5 ciclos passaram de 300 s (Steam inteira 325–643 s em 14–15/10). O que pesa é CPU em Python numa só GIL: `steam_inteira.avaliar` (19 mil itens, 3,5 mi de linhas de histórico) = 13,7 s, rodada **duas vezes por ciclo** (na rápida e na lenta, que mesmo com 1 item baixado reavalia tudo: o log mostra "1 historicos baixados em 79 s"); `ofertas._montar_ofertas` = ~52 s (a `linha_do_tempo` roda ~3x por jogo: `avaliar`, `analisar` e `prever`), disparado por `ofertas.aquecer` no fim de cada ciclo e 3 s depois de cada POST, brigando com a lenta pela GIL. **O cache de Ofertas/Linhas vale 600 s e o ciclo é de 900 s:** nos 5 min finais de cada 15 min a aba Ofertas abre sem cache e espera ~52 s (`/kurokami/ofertas` 52,6 s a frio, 0,19 s quente; `/api/lista` 2,5–3,9 s a frio; Biblioteca 0,4–0,5 s sempre; `/api/progresso`, `/api/resumo`, `/api/vitrine` ≤ 0,03 s, mesmo com o `aquecer` rodando: os 6,8 s vistos antes não se repetiram). Propostas (ganho estimado): (1) cache de Ofertas/Linhas sem prazo de 600 s (só `invalidar`) ou reaquecido antes de vencer: Ofertas abre em < 0,3 s sempre (hoje 52 s em 1/3 do tempo); (2) lenta reavalia só os appids baixados (e nada se `feitos == 0`): 79 s → ~1 s por passada; (3) guardar o resultado de `linha_do_tempo`/`analisar` por jogo (chave: preço, corte, nº e último registro do histórico) e refazer só quem mudou: `avaliar` 13,7 s → ~1 s e `aquecer` 52 s → ~5 s; (4) `aquecer` depois da lenta (não junto) e só em POST que muda dados de Ofertas (carrinho não): tira a briga pela GIL. **Feito em 0.18.6: propostas 1 (cache de 2 h) e 2 (`historicos` reavalia só os baixados e `avaliar` lê só o histórico deles: 14 s → 0,09 s, resultado idêntico em 60 jogos).** Faltam 3 e 4.
- **Status → visual por jogo como a página nova de conquistas da Steam** (pedido do dono, 17/10): ao abrir um jogo no Progresso, uma tela própria com a capa grande, a barra de conquistas, as conquistas feitas e as que faltam (ícone, nome, descrição, raridade em % e data em que pegou), em vez de só a linha da lista. Fonte: `GetPlayerAchievements` (já usado, com `l=brazilian`) + `GetSchemaForGame` (ícones) + `GetGlobalAchievementPercentagesForApp` (raridade).

- **Telegram, o que falta** (base e avisos de oferta feitos na 0.18.0): avisos de **eventos da Steam** (festivais; fonte: feed `store.steampowered.com/feeds/news/app/593110/`), **Humble Bundle** (JSON `landingPage-json-data` de `humblebundle.com/bundles`, ou ITAD `games/bundles/v2`), **campanhas novas da Nuuvem** (links `/promo/<nome>` da home) e **cupons da Nuuvem** (texto de banners/campanhas; sem página pública de cupons). Cada fonte vira um tipo ligável em Notificações → Telegram.
- **Bundles de outras lojas** (Humble, Fanatical) via ITAD `games/bundles/v2`.
- **Hype Games e 2Game**: fora da ITAD; só lendo o site (frágil).
- **Backup automático** semanal do `radar.sqlite3`.
- **Versão multiusuário na nuvem** (discutida, não decidida): Oracle Always Free + login Steam OpenID + Telegram; exigiria pedir permissão de uso às APIs.
- **Guia em PDF** para usuários: ainda não cobre o carrinho direto, a raridade v2 nem o Selo.
- **Faixa do evento da Steam com data de fim** (falta fonte).
- **Keyshops depois de bundles:** quando um jogo entra num bundle (ex.: Humble Choice, que muda na 1ª terça do mês), as keyshops costumam baixar alguns dias depois, quando os revendedores reabastecem. A GG.deals tem API de bundles com histórico; avaliar o aviso "entrou no Humble Choice; keyshops costumam cair nos dias seguintes".
- ~~Decidir se Raro/Ultrarraro sem Selo continuam alertando~~ — resolvido na 0.15 (spec 04): não avisam mais; a raridade só informa ("Costuma voltar").
