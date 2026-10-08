# Pendências e ideias

## Especificações prontas para implementar
- [09 — Biblioteca nova: Coleção por franquias com capas, modo texto, ficha estilo PlayStation](specs/09-biblioteca-nova.md) — **em discussão**; absorve a 03
- [03 — Franquias com capas, cinza e recolher/expandir](specs/03-franquias-com-capas.md) (entra na 09)
- 05 — Veredito na ficha, keyshop decente e limpeza das Configurações (a escrever)
- [07 — Promoções da Steam inteira](specs/07-steam-inteira.md): implementada em 08/10 e revisada na mesma noite (recordes e histórico também fora da lista, menus no topo, sem botão de fonte); falta o teste do dono antes de publicar. Ideia original: Sem login nem perfil público, Promoções mostra a Steam inteira (como a SteamDB) e os filtros pessoais (lista de desejos, seguidos, família, carrinho) aparecem bloqueados com "Entre com a Steam para usar".
- 08 — Layout em etapas: inventário, referência, base visual, uma aba por vez, celular (a escrever)

## Feitas
- [06 — Login Steam: "Entrar pela Steam" (OpenID) feito em v0.16.0; o QR foi descartado e o carrinho vai pela extensão do Radar](specs/06-login-steam.md)
- [04 — Vitrine, aba Promoções e avisos por tipo de recorde (feito em v0.15.0)](specs/04-vitrine-promocoes-e-avisos.md)
- [01 — Raridade v2, Selo Kurokami e fim da avaliação como métrica (feito em v0.14.0)](specs/01-selo-kurokami-e-raridade.md)
- [02 — DLCs não aparecem (feito em v0.13.0)](specs/02-dlcs-nao-aparecem.md)

## Ideias

Em ordem aproximada de valor. Nada aqui foi iniciado.

- **Telegram**: mesmo alerta no celular fora de casa (bot gratuito; token no keyring).
- **Bundles de outras lojas** (Humble, Fanatical) via ITAD `games/bundles/v2`.
- **Hype Games e 2Game**: fora da ITAD; só lendo o site (frágil).
- **Backup automático** semanal do `radar.sqlite3`.
- **Dividir o `painel.html`** (≈80 KB) em CSS/JS separados ou módulos, mantendo sem build.
- **Versão multiusuário na nuvem** (discutida, não decidida): Oracle Always Free + login Steam OpenID + Telegram; exigiria pedir permissão de uso às APIs.
- **Guia em PDF** para usuários: ainda não cobre o carrinho direto, a raridade v2 nem o Selo.
- **Faixa do evento da Steam com data de fim** (falta fonte).
- **Keyshops depois de bundles:** quando um jogo entra num bundle (ex.: Humble Choice, que muda na 1ª terça do mês), as keyshops costumam baixar alguns dias depois, quando os revendedores reabastecem. A GG.deals tem API de bundles com histórico; avaliar o aviso "entrou no Humble Choice; keyshops costumam cair nos dias seguintes".
- ~~Decidir se Raro/Ultrarraro sem Selo continuam alertando~~ — resolvido na 0.15 (spec 04): não avisam mais; a raridade só informa ("Costuma voltar").
