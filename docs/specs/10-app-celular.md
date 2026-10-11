# Spec 10 — App para o celular (APK)

Status: **em discussão, nada implementado** · Pedido do dono em 11/10/2026 ("discutir sobre criar um apk") · Contexto: o PC do dono **não fica ligado o dia inteiro**; o Hunter é um app de Windows (Python + SQLite + painel em `localhost`).

## O que o dono quer do celular (a confirmar)
1. **Ser avisado** de promoções (já resolvido pelo Telegram, 0.18.0, mas só enquanto o PC está ligado).
2. **Ver e navegar** (Ofertas, Biblioteca, ficha) e pôr no carrinho pelo celular.
3. Que isso funcione **com o PC desligado** (é aqui que as opções se separam).

## Opções (da mais barata à mais cara)
| | O que é | Funciona com PC desligado? | Custo | Observação |
|---|---|---|---|---|
| A | **Telegram** (já existe) + painel pela rede local (já existe, com PIN) | não | zero | Resolve o aviso; navegar só no mesmo Wi-Fi. |
| B | **PWA instalável / APK "casca"** (Capacitor ou TWA) abrindo o painel do PC | não | dias | Ícone, tela cheia e `manifest`; fora de casa precisa de VPN (Tailscale) ou túnel. O painel já é responsivo; falta a pendência "Ofertas e Biblioteca no celular" (topo ocupa ~320 px). |
| C | **APK cliente com push** (ntfy ou FCM) | não | 1–2 semanas | O PC continua sendo o servidor; o app só mostra e recebe push. Pouco ganho sobre A + B. |
| D | **App Android independente** (coleta, banco e avaliação no aparelho) | **sim** | semanas a meses | Reescrever a engine (Kotlin/Flutter) ou embarcar Python (Chaquopy). WorkManager periódico tem **mínimo de 15 min e não é garantido** (Doze); a cota da ITAD (~100 chamadas/5 min) passa a ser por aparelho; a chave da ITAD ficaria no celular (Keystore). |
| E | **Servidor na nuvem** (já nas Ideias: Oracle Always Free + login Steam OpenID + Telegram) com app/PWA como cliente | **sim** | semanas | Muda o produto (multiusuário, permissão de uso das APIs, custo de operação). |

## Recomendação provisória
- Para **avisar com o PC ligado**: A (feito) + a Steam inteira avisando (0.18.2).
- Para **ícone no celular**: B, depois de recolher o topo do painel no celular. Instalação do APK por arquivo (sem loja), como a extensão.
- **Só partir para D ou E se o dono precisar de avisos com o PC desligado.** Alternativa barata para esse caso: deixar o Hunter rodando num PC/mini-servidor que fique ligado.

## Perguntas em aberto
1. O que pesa mais: avisos com o PC desligado, ou navegar/comprar pelo celular?
2. Aceita instalar o Tailscale (grátis) no PC e no celular para abrir o painel fora de casa?
3. Distribuição: APK direto por GitHub Releases (como o `.exe`) ou loja?
4. Amigos usariam o app? (Define se D/E valem o custo: cada usuário teria a própria chave da ITAD.)

## Se for B (esboço)
- `manifest.webmanifest` + service worker mínimo servidos por `painel.py` (o painel é uma página só); `display: standalone`, ícones de `assets/`.
- Capacitor: projeto `android/` com `server.url` configurável (IP da rede local ou nome Tailscale); entrada do PIN já existe (`/api/acesso`).
- Ajustes de painel para 375 px: topo recolhido em Ofertas e Biblioteca (pendência já listada).
- Segurança: continua valendo `Host` fixo, PIN e `Origin` nas rotas `/api/steam/*` e `/api/telegram` (só do próprio PC): o app não pode alterar o login Steam nem o Telegram.
