# Kurokami Radar — detalhes técnicos

Monitora a lista de desejos da Steam em várias lojas, guarda o histórico de preços num banco local e avisa pela central de notificações do Windows quando um jogo chega no menor histórico com os seus filtros.

## Uso diário

- `pyw radar.py bandeja` abre o Radar na bandeja, perto do relógio. Ele checa sozinho a cada `intervalos_minutos.itad` (30 min) e notifica.
- `py radar.py inicio instalar` faz ele abrir sozinho quando você entra no Windows (tarefa agendada; sem admin, vira um atalho em Inicializar). `inicio remover` desfaz.
- **Painel** em http://127.0.0.1:8787 (clique no ícone da bandeja): abas *Vale a pena*, *Lista de desejos* (filtros, três visualizações, cartão ao passar o mouse), *Notificações* e *Configurações*. Clicar num jogo abre o histórico de preços por loja, as lojas agora, as formas de comprar e as DLCs, que dá para reclassificar ali mesmo. O painel só aceita conexões do próprio PC.
- **Carrinho** (aba do painel): simule uma compra. Ponha jogos pelo **+** das listas, pela ficha do jogo, pela busca ou trazendo o carrinho da Steam. Escolha a loja de cada um, veja total, economia, quanto falta para os pisos e um orçamento. Se um bundle da Steam cobrir 2+ jogos do carrinho mais barato, ele aparece embaixo, já descontando o que você tem.
- **Adicionar jogo**: busque por nome, appid ou link da Steam. "Só monitorar" coloca um jogo fora da lista de desejos no Radar (fica em `extras` no config); ele ganha preços de todas as lojas e alertas como os outros.
- **Biblioteca** (aba do painel): valor da coleção (cheio, hoje e no menor histórico), quanto falta para completar cada jogo com as DLCs que contam (com as faltantes em promoção destacadas e + para o carrinho), franquias (quantos jogos você tem de cada e quais delas estão na sua lista) e a coleção em grade. A biblioteca é relida 1x por dia; as listas de DLC dos seus jogos se completam em segundo plano.
- **Celular / outro PC**: em Configurações → *Acesso pelo celular*, ligue a rede local. Aparece um link e um QR code com um código de acesso; só aparelhos que abrirem esse link entram. O Windows pode pedir permissão do firewall: escolha "Redes privadas".
- `py radar.py painel` abre só o painel, sem a bandeja.
- Menu da bandeja: **Abrir painel**, **Verificar agora**, **Pausar notificações**, chaves, pasta e log.

Como as notificações funcionam:
- **Na primeira vez** ele não dispara nada em massa: registra o que já está em promoção e manda um aviso só, dizendo quantos são. Daqui pra frente, só novidades.
- Avisa quando um jogo **entra** no menor histórico, ou quando **cai mais** (pelo menos R$ 0,50) depois de já ter avisado.
- Quando a promoção acaba, o jogo rearma e avisa de novo na próxima.
- No máximo 5 notificações por rodada; o resto vira um resumo com botão "Ver lista".
- Horário de silêncio opcional (`notificacoes.silencio`): os avisos ficam guardados e saem quando o silêncio termina.

Teste a notificação com `py radar.py testar-notificacao`. Se não aparecer: Configurações → Sistema → Notificações, e veja se o "Não incomodar" está desligado.

## Instalação

1. Extraia a pasta onde quiser (ex.: `C:\Kurokami Radar`). Tudo que o app cria fica dentro dela, em `dados\`, não importa de onde o terminal foi aberto.
2. Dê dois cliques em `instalar.bat`. Ele instala o `keyring` e abre uma janela para as chaves (Ctrl+V e botão direito funcionam; cada chave é testada antes de salvar):
   - **Steam Web API** (obrigatória) — steamcommunity.com/dev/apikey
   - **IsThereAnyDeal** (obrigatória) — isthereanydeal.com/apps/my
   - **GG.deals** (opcional, para keyshops) — gg.deals/settings, seção Connections

As chaves ficam no **Gerenciador de Credenciais do Windows** (Credenciais do Windows → *Kurokami Radar*), nunca em arquivo. Para trocar depois: `py radar.py chaves` (ou `py radar.py chaves --terminal` sem janela). Para conferir: `py radar.py testar`.

## Instalador .exe (sem Python)

O instalador `KurokamiRadar_Setup_vX.exe` instala o Radar para o seu usuário (sem administrador), com atalho no menu Iniciar, opção de abrir com o Windows e desinstalador em "Aplicativos instalados". O programa vai para `%LOCALAPPDATA%\Programs\Kurokami Radar` e os seus dados (banco, config, carrinho, userdata) para `%LOCALAPPDATA%\Kurokami Radar`. Na primeira vez, ele copia sozinho os dados de `C:\Kurokami Radar`, fecha a versão antiga que rodava pelo código e remove a inicialização automática dela.

Duas formas de gerar o instalador:

- **GitHub (recomendado):** suba esta pasta para um repositório **privado**. O arquivo `.github/workflows/gerar-instalador.yml` faz o GitHub montar o .exe num Windows na nuvem. Para gerar: aba *Actions* → *Gerar instalador* → *Run workflow*, e baixe em *Artifacts*. Ou crie uma tag `v0.9.0` e o instalador aparece em *Releases*. O `.gitignore` impede que `dados/`, `config.json` e `userdata.json` sejam enviados.
- **No seu PC:** instale o Inno Setup 6 e rode `gerar_setup.bat`; o instalador sai em `output\`.

Sem assinatura digital (paga), o Windows pode mostrar "editor desconhecido" na primeira execução: *Mais informações → Executar assim mesmo*.

## Primeiro uso

```bat
py radar.py sondar
py radar.py lojas
py radar.py verificar
```

- `sondar` testa cada API com 3 jogos e salva as respostas cruas em `dados\sonda\sonda.json` (sem chaves, sem dados pessoais). Se algo não bater, é esse arquivo que ajuda a corrigir.
- `lojas` mostra as lojas que a ITAD acompanha no Brasil, com ● nas que você monitora. Ajuste os nomes em `"lojas"` no `config.json` se alguma não for encontrada.
- `verificar` faz a coleta completa e lista o que dispararia notificação agora. **A primeira vez demora**: detalhes da Steam, conteúdo das edições, DLCs, bundles e importação do histórico de cada jogo na ITAD. Partes que usam a loja da Steam (conteúdo de edições e, se a chave não liberar o `GetDLCForApps`, a lista de DLCs) vão a ~1,6s por jogo e ficam em cache por 2 a 4 semanas. Se fechar no meio, retoma de onde parou.

### Edições "parciais"
A Steam às vezes vende uma parte do jogo mais barata no mesmo app — o HITMAN World of Assassination tem a "Part One" a R$ 8,89 ao lado do jogo inteiro. O Radar reconhece o pacote que é o jogo de verdade e marca as partes como **parciais** (não servem para completar). A ITAD acompanha o pacote certo; a GG.deals pega a parte (o HITMAN aparece lá a R$ 8,09), então nesses jogos os números da GG.deals, inclusive keyshop, não entram no histórico nem disparam alerta.

### DRM
Com `somente_drm_steam`, só valem ofertas que a ITAD marca como chave Steam, mais a própria Steam. Oferta com DRM desconhecido fica de fora. Quando a mesma loja aparece duas vezes (outra edição), fica a mais barata com chave Steam.

## Outros comandos

| Comando | O que faz |
|---|---|
| `py radar.py historico hitman` | Histórico de preço por loja, com o menor marcado |
| `py radar.py caminhos hitman` | Base, edições e bundles: seu preço, quanto do conteúdo cobre e quanto custa completar |
| `py radar.py dlcs hitman` | DLCs do jogo e como foram classificadas (história, conteúdo, cosmético, extra, atalho) |
| `py radar.py atualizar --tudo` | Coleta ignorando os intervalos |

## O que o `config.json` controla

- `lojas` e `somente_drm_steam`: onde procurar e se só vale chave ativável na Steam.
- `alerta`: modo (menor histórico), tolerância em %, score mínimo, desconto mínimo, avaliação mínima.
- `keyshops`: só disparam quando o preço é muito baixo — abaixo de `preco_maximo` **ou** abaixo de `pct_do_menor_oficial` % do menor preço oficial — e estão no menor histórico de keyshop.
- `dlc`: ignorar cosméticos, extras (trilha, artbook) e atalhos (boosters, moedas).
- `completo`: por jogo, `"completo"` faz o alerta olhar o custo de ter tudo que importa, em vez do base. O HITMAN já vem marcado.
- `pasta_kurokami_precos`: pasta de outro programa que já tenha um `userdata.json` (opcional).

## Score

`desconto % × qualidade das análises`, de 0 a 100. A qualidade puxa para 70% quando o jogo tem poucas análises, para não supervalorizar um jogo com 12 avaliações. Para o modo completo, o desconto é calculado sobre a soma cheia de base + DLCs relevantes.

## Créditos

Preços de keyshop e menores históricos via [GG.deals](https://gg.deals) e [IsThereAnyDeal](https://isthereanydeal.com).
