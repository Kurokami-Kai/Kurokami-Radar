# Pendências e ideias

## Especificações prontas para implementar
- [01 — Raridade v2, Selo Kurokami e fim da avaliação como métrica](specs/01-selo-kurokami-e-raridade.md)
- [02 — DLCs não aparecem (feito em v0.13.0)](specs/02-dlcs-nao-aparecem.md)
- [03 — Franquias com capas, cinza e recolher/expandir](specs/03-franquias-com-capas.md)

## Ideias

Em ordem aproximada de valor. Nada aqui foi iniciado.

- **Telegram**: mesmo alerta no celular fora de casa (bot gratuito; token no keyring).
- **Bundles de outras lojas** (Humble, Fanatical) via ITAD `games/bundles/v2`.
- **Hype Games e 2Game**: fora da ITAD; só lendo o site (frágil).
- **Backup automático** semanal do `radar.sqlite3`.
- **Dividir o `painel.html`** (≈80 KB) em CSS/JS separados ou módulos, mantendo sem build.
- **Ponte**: confirmar com uso real; ajustar se a Steam mudar `/cart/addtocart`.
- **Versão multiusuário na nuvem** (discutida, não decidida): Oracle Always Free + login Steam OpenID + Telegram; exigiria pedir permissão de uso às APIs.
- **Guia em PDF** para usuários: ainda não cobre a ponte nem a raridade.
