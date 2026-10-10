---
name: editar-painel
description: Editar o painel web (radar/painel.html e radar/painel-web/) sem quebrar nada nem estourar o contexto. Use ao mexer em abas, visual, filtros, carrinho, biblioteca, ficha do jogo, configurações ou qualquer coisa vista no navegador.
---

# Editar o painel

## Localizar
`py tools/mapa.py radar/painel-web [termo]` → arquivo e intervalo; leia só ele. Organização:
- `radar/painel.html`: só o HTML (`<header class="topbar">`, uma `<section id="tab-…">` por aba: `vale`, `lista`, `bib`, `carr`, `notif`, `cfg`; modal `#modal`, `#hv`, `#toast`) e as marcas `/*incluir arquivo*/` dentro do `<style>` e do `<script>`.
- `radar/painel-web/`: CSS (`base.css` tokens e visual Steam, `extras.css`, `configuracoes.css`, `promocoes.css`, `paginas.css`) e JS (`base.js` helpers/estado/blocos/hover/abas, `promocoes.js` tabela com filtros, `ficha.js` modal do jogo, `paginas.js` iframes e `window.KH`, `carrinho.js`, `notificacoes.js`, `configuracoes.js`, `conta.js` conta Steam e Finalizar pedido, `status.js` `VERSAO_PAGINA` e ações).
- O `painel.py` (`montar_painel`) junta tudo numa página só, **num `<script>` só**: os arquivos de JS dividem o mesmo escopo e rodam na ordem das marcas; `function` serve antes de onde está escrita, `const`/`let` não (TDZ).
- Arquivo novo em `painel-web/`: crie a marca no `painel.html` (o `checar.py` falha se faltar) e ele já vai no instalador (a pasta inteira está no `--add-data`).

## Ofertas e Biblioteca são outras páginas
`radar/ofertas.html` (Destaques, Promoções, Lista) e `radar/biblioteca.html` (Coleção/Franquias, Completar) abrem num iframe nas abas `#vale` e `#bib`; os dados vêm de `radar/ofertas.py` (no lugar de `/*DADOS*/{}`). Têm CSS e JS próprios (os das amostras da spec 09). Ficha do jogo, carrinho e loja: `parent.KH` (definido no `painel.html`, seção "Ofertas e Biblioteca"). Teste em `/kurokami/ofertas` direto também (sem o painel em volta, as ações avisam por toast).

## Padrões que já existem (reutilize, não recrie)
- Dados: `api(url)` e `post(url, corpo)` (já mostram erro em toast). Lista em `L`/`IDX`, carrinho em `CARR`, resumo em `RES`.
- Render por aba: `renderVale`, `renderLista`, `renderBib`, `renderCarr`, `renderNotif`, `renderCfg`; `render()` chama a da aba atual.
- Peças: `art()` (capa com reserva), `priceBlock()`, `flags()`, `rarPill()`, `cartBtn()`/`cartBtnB()`, `brl()`, `esc()`, `toast()`, `fmtISO()`.
- Cliques por delegação: `data-open` (ficha), `data-cart`/`data-cartb` (carrinho), `data-hv` (hover).
- Estado salvo em `localStorage` via `ls.get/ls.set` e `save()`.

## Regras
- Todo texto vindo de dado passa por `esc()`.
- Só preto e vermelho, cada vermelho com um papel: `--acao` (comprar), `--sinal` (ativo/importante), `--blue` (clicável); botão secundário cinza; desconto pela escala `data-calor` (ver `docs/decisoes-visual.md`, "Paleta por papel"). Use as variáveis do `:root`.
- Pensar no celular: o painel também abre no telefone (media queries `max-width:720px/900px`).
- Campo novo de API → documentar em `docs/api.md` e criar no `painel.py`.
- Mudou o painel junto com o servidor → mesma versão em `VERSAO_PAGINA` e `radar/__init__.py`.

## Testar
- `py tools/checar.py` (valida o JS).
- Visual: `py radar.py painel` e abrir `http://127.0.0.1/kurokami`; olhe o console do navegador.
- **Confira pelo DOM, não por print:** `read_page`/`get_page_text` para texto e estrutura, `javascript_tool` com `getComputedStyle`/`getBoundingClientRect` para cor, tamanho e alinhamento (um laço cobre várias abas de uma vez). Print só no fim, um por mudança, com `scale: 0.5`.
