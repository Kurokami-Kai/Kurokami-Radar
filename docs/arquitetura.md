# Arquitetura

Kurokami Radar é um app **local** de Windows (Python 3.12) que monitora a lista de desejos da Steam em várias lojas, guarda o histórico de preços em SQLite, notifica pela central do Windows e serve um painel web em `http://localhost/kurokami`. Não existe servidor do projeto: cada usuário roda tudo no próprio PC, com as próprias chaves de API.

## Visão geral

```
                    ┌──────────── bandeja.py (pystray, thread principal) ────────────┐
                    │  menu do ícone · tooltip com progresso · verificação de versão  │
                    └──────┬───────────────────────────────┬────────────────────────┘
                           │                               │
             servico.Servico (thread)            painel.py (ThreadingHTTPServer, thread)
             a cada N min: ciclo()               GET/POST /api/*  ·  /kurokami (painel.html)
                           │                               │
   ciclo(): coleta.atualizar → analise.avaliar → notificador.processar → relatorio
                           │
    ┌──────────────┬───────┴────────┬───────────────┐
  steam.py        itad.py        ggdeals.py      (rede.py: HTTP, ritmo, backoff)
                           │
                     banco.py (SQLite em dados/radar.sqlite3)
```

- **Processo único.** A bandeja é o processo principal. O serviço de coleta e o servidor do painel são threads dele. Uma porta-trava (`127.0.0.1:47811`) impede duas cópias.
- **Janelas Tk** (chaves, atualização) rodam em **processo separado** (`KurokamiRadar.exe chaves` / `atualizar-app`), porque o pystray ocupa a thread principal.
- **Notificações**: `notificar.py` monta XML de toast e chama PowerShell (`-EncodedCommand`, janela oculta). O app se registra em `HKCU\Software\Classes\AppUserModelId\Kurokami.Radar` para aparecer com nome e ícone.

## Fontes de dados e o papel de cada uma

| Fonte | Usada para | Limites conhecidos |
|---|---|---|
| Steam `IStoreBrowseService/GetItems` (sem chave) | catálogo da lista, preços Steam, análises, edições/pacotes, bundles, capas, franquia, fim do desconto | lotes de 50; sem limite publicado |
| Steam `GetWishlist` (sem chave) | lista de desejos e prioridade | perfil precisa ter "Detalhes dos jogos" público |
| Loja Steam (`appdetails`, `packagedetails`) | lista de DLCs de cada jogo; conteúdo das edições | ~200 chamadas / 5 min (ritmo 1,6 s); `GetDLCForApps` exige chave de parceiro, por isso este plano B |
| Steam Web API (chave opcional) | `ResolveVanityURL` (plano B), `GetOwnedGames` | — |
| `userdata.json` (opcional, manual) | DLCs que o usuário possui, carrinho da Steam | é um retrato; envelhece |
| IsThereAnyDeal (chave obrigatória) | preços em ~34 lojas BR (com DRM), histórico (`history/v2`), menor histórico, expiração da oferta | limita ritmo; 200 ids por chamada de preços |
| GG.deals (chave opcional) | melhor preço oficial e keyshop + mínimos | atualiza 1x/h; não diz a loja; erra em jogos com "edição parcial" |

## Ciclo de coleta (`coleta.atualizar`)

1. Perfil → SteamID (XML público do perfil; API como reserva). Lista de desejos (+ `extras` do config). Biblioteca = `userdata.json` ∪ `GetOwnedGames` ∪ `tenho_manual`.
2. **Catálogo Steam** (a cada `intervalos_minutos.steam`, ou forçado): detalhes da lista, conteúdo das edições, listas de DLC (plano B pela loja, com orçamento `chamadas_lentas_por_rodada`), bundles e itens de bundles. Se sobrar fila lenta, o catálogo roda de novo no próximo ciclo.
3. **Biblioteca** (1x/dia): detalhes de tudo que o usuário tem + menor histórico na ITAD das DLCs que faltam.
4. **ITAD**: mapeia appid→id ITAD; importa histórico uma vez por jogo (todas as lojas); preços atuais de todas as lojas → `preco` (só quando muda) e `oferta_atual` (snapshot vigente).
5. **GG.deals** (a cada 60 min).
6. **Custo completo** dos jogos em modo "completo" vira uma "loja" própria no histórico (`Completo (Steam)`).

Verificação **rápida** = o ciclo normal (respeita intervalos e orçamento). **Completa** = `forcar=True, sem_limite=True`; a primeira é sempre completa, depois a cada `verificacao_completa_dias`.

## Avaliação (`analise.avaliar`)

Por jogo da lista (exceto os que o usuário já tem): para cada oferta das **lojas marcadas** (e DRM Steam, se exigido) roda `analise.analisar(linhas, preco, corte)`:
- `linha_do_tempo` junta o histórico das lojas marcadas em trechos (menor preço, corte do menor, maior corte); `episodios` vira promoções (intervalo sem desconto < 1 dia não separa).
- **Raridade** (eixo 1): episódios anteriores com corte ≥ atual − 5, por ano, nos últimos 24 meses. Comum ≥ 3/ano · Incomum 1,5–3 · Raro 0,75–1,5 · Ultrarraro < 0,75 · Lendário = nunca (histórico inteiro), com ≥ 24 meses de histórico e ≥ 1 promoção anterior; 12–24 meses: no máximo Ultrarraro. Sem promoção anterior nas lojas marcadas ou histórico < 6 meses: no máximo Incomum.
- A raridade não aparece mais nas telas (0.15): vira a coluna informativa **"Costuma voltar"** (`costuma_voltar`: histórico curto · primeira promoção · nunca teve esse desconto (histórico inteiro) · não teve nos últimos 2 anos · todo mês · a cada ~N meses · 1 vez por ano · 1 vez em 2 anos; `dica_volta` dá a linha "Nos últimos 2 anos: N vezes com -Y% ou mais…").
- **No piso** (eixo 2): corte ≥ maior corte da vida − 5, ou preço ≤ menor de 24 meses + 1%.
- **Tipo de preço** (reais): compara com o menor preço *antes* do episódio de preço atual (`piso_ref`, o menor de sempre): `piso_tipo` novo / raro (≥ 18 meses sem esse nível ou ≤ 50% do recorde) / igual / 24m (igual ao menor dos últimos 24 meses).
- **Selo Kurokami (0.15)** = só G: `piso_tipo == "raro"` + ≥ 1 promoção anterior nas lojas marcadas + corte ≥ `selo_corte_minimo`. `selo_motivo`: "preço caiu pela metade ou mais (o menor anterior era R$ X, mm/aaaa)" ou "o menor preço anterior (R$ X) foi há N meses". O Lendário (F) não dá mais Selo (escada de descontos; ver `decisoes.md`).
  - *Frase para os textos do usuário (referência):* "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade".
- `tipos_de(an)` = lista não exclusiva: `selo` se Selo; `novo` se `piso_tipo` novo ou raro; `igual`; `24m`. `tipo_oferta` = o primeiro de [selo, novo, igual, 24m] (vitrine, "Mostrar só", título do aviso).
- **Score** fica só interno (corte × peso da raridade + 10 no piso). Análises não entram em nada.

**Avisa** (`avisa_por`) se algum tipo da oferta está ligado em `alerta.tipos` e (é o Selo, que já tem o `selo_corte_minimo`, ou corte ≥ `desconto_minimo`). Raridade e favoritos não decidem nada. Motivo por tipo (`motivo_tipo`). Modo completo e keyshop têm regras próprias. Saída agrupada: um alerta por jogo, na ordem selo, novo, igual, 24m e, dentro de cada, maior corte (`chave_aviso`).

**Régua da Steam** (`regua_steam`): só informativa. Se a Steam sozinha ("Steam (direto)" + Steam da ITAD) dá Novo recorde ou Selo e as lojas marcadas não, a ficha diz "Na Steam, é o menor preço já registrado. Nas suas lojas, <loja> já teve R$ X (mm/aaaa)." (`menor_anterior` acha o registro que impediu).

## Notificação (`notificador.Notificador`)

Linha de base na primeira vez (não dispara nada em massa) → ao **ligar um tipo** (`meta.tipos_ligados` muda), quem já estava assim e só avisaria por ele entra em `notificado` sem toast e sai um resumo "<Tipo> ligado: N jogos já estão assim agora…" com "Ver" (abre `#vale`) → avisa novidades, quedas ≥ `melhora_minima_reais` e jogos que "rearmaram" (saíram e voltaram). Respeita pausa, horário de silêncio (guarda pendentes), máximo por rodada (resto vira resumo) e silenciados. Avisos de "termina em breve" para carrinho/o que avisa. Título por tipo ("SELO KUROKAMI · …", "Novo recorde · …", "Igual ao recorde · …", "Menor em 2 anos · …"), nunca por raridade.

## Painel

`painel.html` é um SPA único (HTML+CSS+JS inline, sem build), visual da loja Steam. Lê tudo via `/api/*` (ver `api.md`). Abas: **Vale a pena** = vitrine (`/api/vitrine`: carrossel do Selo e prateleiras Novo recorde, Igual ao recorde, Menor em 2 anos), **Promoções** = explorador com filtros **no servidor** (`/api/promocoes`, pensando na Steam inteira, spec 07), Biblioteca (com "DLCs em promoção"), Carrinho, Notificações, Configurações ("O que te avisa"). O endereço guarda a aba (`#vale`, `#lista`…).

**Cache das linhas** (`painel.linhas_promocoes`): uma linha por jogo da lista, montada em ~0,5 s e guardada em memória com trava; filtrar/ordenar nele custa milissegundos. É refeito quando termina uma coleta (`servico.ciclo`), em qualquer POST do painel, quando o config ou o `userdata.json` muda (assinatura) e, por segurança, a cada 10 min. `/api/lista` também usa o cache. Seguidos/ignorados vêm de `conta_steam.relacao` (único leitor do `userdata.json` para isso). Localhost sempre liberado; outros aparelhos só com PIN (cookie `kr`) e se `painel.rede_local` estiver ligado. Porta 80 com reserva na 8787.

## Conta Steam (opcional)

**Entrar pela Steam** (`steam_openid.py`, OpenID 2.0, opcional): só o SteamID, gravado em `perfil_steam`. **Finalizar pedido** (aba Carrinho): `POST /api/steam/carrinho` devolve o endereço `store.steampowered.com/cart/#kurokami=…` com os pacotes/bundles e modos; o painel o abre numa aba e a extensão do Radar (`extensao/`: `carrinho.js` na página do carrinho, `fundo.js` faz as chamadas a `IAccountCartService`, `painel.js` só marca `data-kurokami-ext` no painel) põe os itens com a sessão da própria página, confere e recarrega. Sem a extensão, o painel mostra como carregá-la ("Carregar sem compactação"). Ver `docs/decisoes.md`, "Login Steam".

## Distribuição

- **Pelo código**: `KurokamiRadar_Setup_vX.bat` (payload base64 de um zip) instala em `C:\Kurokami Radar`.
- **Instalado**: GitHub Actions → PyInstaller (onedir, windowed) → Inno Setup → `KurokamiRadar_Setup_vX.exe` em Releases. Programa em `%LOCALAPPDATA%\Programs\Kurokami Radar`, dados em `%LOCALAPPDATA%\Kurokami Radar` (`caminhos.py` decide pelo `sys.frozen`).
- **Atualização**: `atualizador.py` consulta `api.github.com/repos/<atualizacao.repo>/releases/latest` ao abrir e a cada 24 h; baixa o `.exe` do release e roda `/VERYSILENT`; o instalador reabre o app (`Check: WizardSilent`).
