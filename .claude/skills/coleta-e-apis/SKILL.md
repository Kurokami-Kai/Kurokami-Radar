---
name: coleta-e-apis
description: Regras da coleta de preços e das integrações Steam, ITAD e GG.deals (ritmo, lotes, cache, progresso, falhas). Use ao mexer em steam.py, itad.py, ggdeals.py, coleta.py, rede.py ou ao adicionar fonte de dados.
---

# Coleta e APIs

Antes: leia `docs/decisoes-coleta.md` e a parte "Fontes de dados" de `docs/arquitetura.md`.

## Regras
- **Lote sempre que existir**: GetItems 50/chamada, ITAD preços 200, GG.deals 100. Nunca um item por chamada se houver lote.
- **Ritmo**: use `rede.http_json(..., ritmo=RITMO[...])` — ele espera, reduz o passo em 429 e repete em 5xx. Loja Steam (`appdetails`/`packagedetails`) = ~1,6 s por chamada.
- **Consultas lentas** entram no orçamento `chamadas_lentas_por_rodada` e no cache `consulta_lenta` (com validade). A verificação completa ignora o orçamento.
- **Tolerar falha**: lote recusado → registra no log e segue. Chave recusada → mensagem com o motivo (`rede.explicar`).
- **Progresso**: linha de log sem recuo = etapa nova no painel; em laços longos chame `progresso.passo(i, total)`.
- **Gravar**: preços com `banco.registrar_preco` (só grava se mudou); ofertas vigentes com `salvar_ofertas_atuais`; `commit()` ao fim de cada etapa (o painel grava em paralelo).
- **Valores**: centavos; `rede.centavos` (Steam) vs `rede.de_reais` (ITAD/GG); datas em UTC.
- **Preço de agora** = `oferta_atual`, nunca o último registro do histórico.
- Não usar várias chaves para driblar limite.

## Fonte nova
1. Cliente em módulo próprio (`radar/<fonte>.py`) com função de lote e exceção `ChaveRecusada`.
2. Chave (se houver) em `credenciais.CHAVES` + validação em `validar.py` + campo na `janela_chaves.py`.
3. Etapa em `coleta.atualizar` com intervalo próprio em `config.intervalos_minutos`.
4. Documentar em `docs/arquitetura.md` (tabela de fontes) e `docs/decisoes-coleta.md` se houver pegadinha.

## Testar
`py radar.py sondar <appid>` salva respostas cruas em `dados/sonda/sonda.json`: confira o formato real antes de escrever o parser.
