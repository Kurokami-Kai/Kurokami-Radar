# Novidades

Texto para a descrição do release (aparece na janela de atualização). A seção de cima é a próxima versão.

## 0.15.0 (publicada em 2026-10-04)
- **Você escolhe o que te avisa.** Em Configurações → "O que te avisa", quatro tipos de preço: **Selo Kurokami** (ligado), **Novo recorde**, **Igual ao recorde** e **Menor em 2 anos**. Cada um mostra quantos avisos costuma dar por semana. Fora o Selo, só avisam com o desconto mínimo.
- **Selo Kurokami mais exigente:** agora é "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade". "Pela metade" aceita centavos de diferença (até R$ 0,10 ou 1%), como o "igual ao recorde". O "maior desconto da história" deixou de dar Selo (jogos que sobem o desconto um pouco a cada ano ganhavam Selo todo ano). **Os Selos de hoje, todos desse tipo, deixam de ser Selo.** Nos dados de 2022–2025, em cerca de 7 de 10 Selos o jogo não ficou mais barato nos 12 meses seguintes.
- **Raro, Ultrarraro e Lendário saíram das telas e dos avisos.** No lugar, a coluna **"Costuma voltar"** diz com que frequência aquele desconto aparece ("todo mês", "a cada ~3 meses", "1 vez por ano", "nunca teve esse desconto"...). Só informa, não decide aviso.
- **Favoritos não têm mais regra especial de aviso**: todos os jogos seguem as mesmas caixas.
- **Ligar um tipo não enche a tela de avisos:** os jogos que já estão assim entram sem notificação e chega um resumo ("Novo recorde ligado: 28 jogos já estão assim agora...").
- **"Vale a pena" virou uma vitrine** como a da loja Steam: carrossel do Selo Kurokami e prateleiras Novo recorde, Igual ao recorde e Menor em 2 anos, cada jogo em uma só, com "Ver tudo".
- **"Lista de desejos" virou "Promoções"**, um explorador como o da SteamDB: filtros que se combinam (relação com o jogo com ✓/✕, Mostrar só, Tipo, Outros, preço, análises, nota, desconto, lançamento), chips com × para tirar cada filtro, tabela com ordenação por coluna (Shift+clique soma critérios), 50/100/250 por página e grade. Abre com "Desconto ≥ 50%" e "Análises ≥ 5.000"; "Restaurar padrão" volta a eles.
- A ficha mostra **"Termina em"** sempre que há data, o "Costuma voltar" e, quando só a Steam tem o recorde, uma linha como "Na Steam, é o menor preço já registrado. Nas suas lojas, Nuuvem já teve R$ 4,74 (07/2025)."
- Biblioteca → **"DLCs em promoção"**: as DLCs que faltam nos seus jogos e estão com desconto agora.
- O motivo do aviso cita a data do preço de verdade: "o menor anterior era R$ 4,74, 07/2025" (antes podia sair a data de um preço de centavos diferente, que só conta como o mesmo nível).
- Correção: no ícone da bandeja, "Abrir pasta dos dados" e "Ver log" não faziam nada. Agora abrem (o log é criado vazio se ainda não existir).

## 0.14.0 (publicada em 2026-10-04)
- **Raridade nova:** mede quantas vezes por ano o jogo chega àquele desconto, não o preço em reais. Promoções que se repetem não saem mais como *Lendário* (ex.: Castle of Illusion a 80%, quando 75% acontece todo mês).
- **Selo Kurokami:** um selo dourado quando o jogo está na melhor oferta da história dele: o maior desconto ou o menor preço em muito tempo. A notificação diz qual: "maior desconto da história (-85%; antes, no máximo -80%)" ou "menor preço já registrado (dados desde mm/aaaa)". Sempre avisa, com "SELO KUROKAMI" no título. Dá para exigir um desconto mínimo em Configurações.
- **Pílula de piso** ao lado do preço: *Novo recorde*, *Recorde raro*, *Igual ao recorde*, *Menor em 24 meses* ou o menor preço já visto, em cinza.
- *Lendário* exige 2 anos ou mais de histórico e alguma promoção anterior; jogos mais novos chegam no máximo a *Ultrarraro*.
- A ficha do jogo explica a raridade: maior desconto da vida, quantas vezes chegou nesse nível em 24 meses e quando foi a última.
- **Análises da Steam não decidem mais alertas** (o jogo já está na sua lista). Saíram das Configurações "Score mínimo", "Análises positivas mínimas" e "Ignorar sem análises".
- Os avisos de **"termina em breve"** respeitam o limite por rodada: o resto vira um resumo ("+N terminando em breve").
- **Notificação mais limpa:** sem score; com Selo, o texto começa direto no motivo; lojas com o mesmo preço aparecem como "mesmo preço na Nuuvem" (ou "na GOG por +R$ 0,45", até R$ 1 a mais).
- Correção: quem nunca ordenou a lista de desejos na Steam tinha **todos** os jogos tratados como favoritos.

## 0.13.0 (publicada em 2026-10-03)
- **A primeira verificação agora é completa:** lê as DLCs de todos os jogos de uma vez, sem esperar várias rodadas.
- **Atualizando da 0.12:** a primeira abertura faz uma verificação completa (30 a 40 min), porque a 0.12 nunca a registrou. Deixe o Radar aberto até terminar.
- A ficha do jogo explica quando não há DLCs: lista ainda na fila (com o progresso), a Steam não informou ou a consulta falhou.
- Se a consulta de DLCs de um jogo falhar, ele é tentado de novo na próxima verificação.
