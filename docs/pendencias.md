# Pendências e ideias

## Especificações prontas para implementar
- [03 — Franquias com capas, cinza e recolher/expandir](specs/03-franquias-com-capas.md)
- [04 — Filtros, colunas e "DLCs em promoção"](specs/04-filtros-e-colunas-da-lista.md) — a 01 já está feita (v0.14.0)

## Feitas
- [01 — Raridade v2, Selo Kurokami e fim da avaliação como métrica (feito em v0.14.0)](specs/01-selo-kurokami-e-raridade.md)
- [02 — DLCs não aparecem (feito em v0.13.0)](specs/02-dlcs-nao-aparecem.md)

## Ideias

Em ordem aproximada de valor. Nada aqui foi iniciado.

- **Telegram**: mesmo alerta no celular fora de casa (bot gratuito; token no keyring).
- **Bundles de outras lojas** (Humble, Fanatical) via ITAD `games/bundles/v2`.
- **Hype Games e 2Game**: fora da ITAD; só lendo o site (frágil).
- **Backup automático** semanal do `radar.sqlite3`.
- **Dividir o `painel.html`** (≈80 KB) em CSS/JS separados ou módulos, mantendo sem build.
- **Ponte**: confirmar com uso real; ajustar se a Steam mudar `/cart/addtocart`.
- **Versão multiusuário na nuvem** (discutida, não decidida): Oracle Always Free + login Steam OpenID + Telegram; exigiria pedir permissão de uso às APIs.
- **Guia em PDF** para usuários: ainda não cobre a ponte, a raridade v2 nem o Selo.
- **Faixa do evento da Steam com data de fim** (falta fonte).
- **Carrinho:** repensar a aba e avaliar alternativas à ponte do Tampermonkey. Só anotação, nada decidido.
- **Keyshops depois de bundles:** quando um jogo entra num bundle (ex.: Humble Choice, que muda na 1ª terça do mês), as keyshops costumam baixar alguns dias depois, quando os revendedores reabastecem. A GG.deals tem API de bundles com histórico; avaliar o aviso "entrou no Humble Choice; keyshops costumam cair nos dias seguintes".
- **Promoções fora da lista de desejos** (a SteamDB mostra a Steam inteira): exigiria outra fonte de dados e mudaria o tamanho da coleta. Só ideia.
- Decidir se Raro/Ultrarraro sem Selo continuam alertando (backtest: 53,5% não batido, igual a promoção no piso) — junto com a spec 05.
