---
name: editar-painel
description: Como editar o painel web do Kurokami Hunter (radar/painel.html - HTML, CSS e JS num arquivo só) sem quebrar nada nem estourar o contexto. Use sempre que a tarefa mexer em abas, visual, filtros, carrinho, biblioteca, ficha do jogo, configurações ou qualquer coisa que o usuário veja no navegador.
---

# Editar o painel

## Localizar
`py tools/mapa.py radar/painel.html [termo]` → leia só o intervalo. Organização:
- `<style>`: CSS base (visual Steam) e depois `/* ---------- painel: extras ---------- */`.
- HTML: `<header class="topbar">`, depois uma `<section id="tab-…">` por aba (`vale`, `lista`, `bib`, `carr`, `notif`, `cfg`), modal `#modal`, `#hv` (hover), `#toast`.
- `<script>` dividido por marcadores `/* ================= nome ================= */`: helpers, estado, blocos, hover, abas, vale a pena, lista, modal do jogo, biblioteca, carrinho, notificações, configurações, status / ações.

## Padrões que já existem (reutilize, não recrie)
- Dados: `api(url)` e `post(url, corpo)` (já mostram erro em toast). Lista em `L`/`IDX`, carrinho em `CARR`, resumo em `RES`.
- Render por aba: `renderVale`, `renderLista`, `renderBib`, `renderCarr`, `renderNotif`, `renderCfg`; `render()` chama a da aba atual.
- Peças: `art()` (capa com reserva), `priceBlock()`, `flags()`, `rarPill()`, `cartBtn()`/`cartBtnB()`, `brl()`, `esc()`, `toast()`, `fmtISO()`.
- Cliques por delegação: `data-open` (ficha), `data-cart`/`data-cartb` (carrinho), `data-hv` (hover).
- Estado salvo em `localStorage` via `ls.get/ls.set` e `save()`.

## Regras
- Todo texto vindo de dado passa por `esc()`.
- Visual da loja Steam (cores `--blue`, `--disc-bg`, `--price-bg`…); use as variáveis do `:root`.
- Pensar no celular: o painel também abre no telefone (media queries `max-width:720px/900px`).
- Campo novo de API → documentar em `docs/api.md` e criar no `painel.py`.
- Mudou o painel junto com o servidor → mesma versão em `VERSAO_PAGINA` e `radar/__init__.py`.

## Testar
- `py tools/checar.py` (valida o JS).
- Visual: `py radar.py painel` e abrir `http://127.0.0.1/kurokami`; olhe o console do navegador.
