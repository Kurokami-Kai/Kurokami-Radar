# Spec 03 — Franquias com capas, cinza para o que falta, recolher/expandir

Status: **a implementar** · Skills: `editar-painel`, `testar-sem-rede`

## Pedido (dono, 03/10)
- Na aba Biblioteca → Franquias, mostrar **capas** dos jogos em vez de lista de texto.
- Jogos que **tenho**: capa colorida. Jogos que **não tenho**: capa em **cinza** (grayscale).
- Algumas capas já são preto e branco → precisa de um **identificador extra** além da cor.
- Poder **minimizar e maximizar** cada franquia.

## Proposta
- Card da série: cabeçalho (nome, "tenho N de M", barra de valor que já existe, botão ▾/▸), corpo com **grade de capas verticais** (`capa_v`, reserva `capa`).
- Estado por capa:
  - **Tenho**: colorida + selo pequeno "✓" no canto (verde).
  - **Não tenho, na lista de desejos**: `filter: grayscale(1) brightness(.75)` + selo "♡" ou preço/desconto no rodapé + botão **+** do carrinho.
  - **DLCs faltando** num jogo que tenho: selo âmbar "N DLC".
  - O identificador (✓ / preço) garante a leitura mesmo em capa naturalmente P&B. Também `title`/hover com o estado por extenso.
- Recolher/expandir: clique no cabeçalho; estado salvo em `localStorage` (`ls.set`); botões "Expandir todas" / "Recolher todas" na barra da aba. Recolhida mostra só cabeçalho + até 6 miniaturas.
- Clique na capa abre a ficha do jogo (`data-open`).

## Arquivos
- `painel.html`: seção `biblioteca` (`renderBib`, ramo `franquias`) + CSS novo (grade de capas, estados, selos). Nada no servidor: `api_biblioteca` já devolve `tenho[]` e `lista[]` com `capa`; acrescentar `capa_v` nesses itens em `painel.py`.

## Aceite
- Série "Need for Speed" (exemplo): capas lado a lado, as que tenho coloridas com ✓, as da lista em cinza com preço e +.
- Estado recolhido persiste ao recarregar.
- Funciona no celular (grade com 3 colunas em `max-width:720px`).
