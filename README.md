# Kurokami Radar

Monitora a sua **lista de desejos da Steam** em dezenas de lojas, guarda o **histórico de preços** no seu PC e avisa pela **central de notificações do Windows** quando um jogo chega no menor preço em muito tempo (Selo Kurokami) ou nos tipos de recorde que você escolher. Tem um painel no navegador com lista, biblioteca de colecionador, carrinho simulado com bundles e acesso pelo celular.

Tudo roda no seu PC. Nada é enviado para servidor nenhum além das consultas às lojas (Steam, IsThereAnyDeal e GG.deals).

---

## 1. Instalar

1. Baixe o **`KurokamiRadar_Setup_vX.exe`** na página **Releases** deste repositório.
2. Abra o arquivo. Se o Windows mostrar *"O Windows protegeu o computador"*, clique em **Mais informações → Executar assim mesmo** (o programa não tem assinatura digital paga).
3. Siga o instalador. Não precisa de administrador nem de Python.

No fim, o Radar abre sozinho e mostra a janela **Perfil e chaves**. É só preencher como explicado abaixo.

---

## 2. O que você precisa preencher

| Campo | Obrigatório? | Para que serve |
|---|---|---|
| Perfil Steam | **sim** | saber qual lista de desejos e biblioteca olhar |
| Chave da IsThereAnyDeal | **sim** | preços de dezenas de lojas e histórico |
| Chave da GG.deals | não | preços de keyshops (só avisa quando estiver muito barato) |
| Chave da Steam Web API | não | ler a biblioteca quando você não tem o `userdata.json` |

As chaves ficam guardadas no **Gerenciador de Credenciais do Windows** (nunca num arquivo). Dá para trocar depois pelo menu do ícone: **Chaves e perfil…**

### Perfil Steam

1. Abra o seu perfil na Steam (no app: clique no seu nome → *Perfil*; no navegador: steamcommunity.com/my/profile).
2. Copie o endereço. Fica como `https://steamcommunity.com/id/seunome` ou `https://steamcommunity.com/profiles/7656119...`.
3. Cole no campo **Seu perfil Steam**.

**Ou entre pela Steam** (como no ITAD ou na SteamDB): no painel, botão *Entrar pela Steam* no canto superior direito (em qualquer aba). Você confirma na página da própria Steam e o Radar só recebe o seu SteamID: nunca a senha, nem token, nem cookie. Só funciona abrindo o painel no próprio PC.

**A lista de desejos precisa estar pública.** Na Steam: *Perfil → Editar perfil → Configurações de privacidade → Detalhes dos jogos = Público*. Se estiver privada, a janela avisa "a lista de desejos veio vazia".

### Chave da IsThereAnyDeal (obrigatória, gratuita)

1. Crie uma conta em **isthereanydeal.com** (canto superior direito, *Sign in*).
2. Acesse **isthereanydeal.com/apps/my** e clique para **registrar um app**. O nome pode ser qualquer um (ex.: `Kurokami Radar`).
3. Na página do app, copie o campo **API Key**.
   ⚠️ Não é o *OAuth Client ID* nem o *Client Secret*.
4. Cole no campo **IsThereAnyDeal**.

### Chave da GG.deals (opcional, gratuita)

1. Crie uma conta em **gg.deals** e confirme o e-mail.
2. Acesse **gg.deals/settings**, seção **Connections**, e copie a **GG.deals API key**.
3. Cole no campo **GG.deals**.

### Chave da Steam Web API (opcional, gratuita)

Só faz diferença se você **não** usar o `userdata.json` (próxima seção).

1. Acesse **steamcommunity.com/dev/apikey** logado na Steam.
2. Em *Domain Name*, escreva qualquer coisa (ex.: `localhost`), aceite os termos e clique em *Register*.
3. Copie a **Key** (32 letras e números) e cole no campo **Steam Web API**.

Clique em **Salvar**. Cada campo é testado na hora: ✓ verde está certo; ✗ vermelho mostra o motivo.

---

## 3. Opcional: suas DLCs (`userdata.json`)

A Steam só informa publicamente os **jogos** que você tem, não as **DLCs**. Sem elas, o Radar não sabe quais DLCs você já comprou (afeta a aba Biblioteca e o preço de bundles). Para incluir:

1. No navegador, **logado na Steam**, abra: `https://store.steampowered.com/dynamicstore/userdata/`
2. Aparece um texto grande. Salve com **Ctrl+S** com o nome **`userdata.json`**.
3. Coloque o arquivo em `%LOCALAPPDATA%\Kurokami Radar` (cole esse endereço na barra do Explorador). Ou use o menu do ícone: **Abrir pasta dos dados**.

Repita de vez em quando: o painel avisa quando o arquivo tiver mais de 30 dias. Esse arquivo é **seu**: não compartilhe com ninguém.

---

## 4. Usando

- O Radar fica no **ícone perto do relógio**. Ele checa os preços sozinho a cada 30 minutos.
- **Clique no ícone** para abrir o painel (`http://localhost/kurokami`).
- **A primeira checagem demora** (uns 10 a 40 minutos, conforme o tamanho da sua lista): ela importa o histórico de cada jogo e lê DLCs e bundles. Depois, cada checagem leva segundos.
- Na primeira vez ele **não** dispara uma enxurrada de avisos: registra o que já está em promoção e daí em diante avisa só as novidades.

### Abas do painel

- **Vale a pena:** a vitrine, como as prateleiras da loja Steam. No topo, o carrossel do **Selo Kurokami** (dourado): *o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade*. Nos dados de 2022–2025, em cerca de 7 de 10 casos assim o jogo não ficou mais barato nos 12 meses seguintes. Abaixo, as prateleiras **Novo recorde** (nunca esteve tão barato), **Igual ao recorde** e **Menor em 2 anos**, com o desconto mínimo das Configurações. Cada jogo aparece em uma prateleira só; "Ver tudo" abre a lista completa em Promoções.
- **Promoções:** todos os jogos da sua lista, num explorador como o da SteamDB. Filtros que se combinam: sua relação com o jogo (✓ só esses, ✕ esconder: na lista, monitorado, no carrinho, silenciado, tenho...), Mostrar só (os 4 tipos de preço), Tipo, Outros, preço, análises, nota, desconto e lançamento. Cada filtro ativo vira um chip com ×. A tabela ordena clicando no título da coluna (Shift+clique soma critérios) e tem a coluna **Costuma voltar** ("todo mês", "a cada ~3 meses", "1 vez por ano", "nunca teve esse desconto"...), que só informa. Abre com "Desconto ≥ 50%" e "Análises ≥ 5.000"; "Restaurar padrão" volta a eles. No celular, os filtros ficam no botão **Filtros**. Clique num jogo para ver o histórico em gráfico, as lojas, as formas de comprar, quando a promoção termina e as DLCs. Se só a Steam tiver o recorde, a ficha avisa ("Na Steam, é o menor preço já registrado. Nas suas lojas, Nuuvem já teve R$ 4,74 (07/2025).").
- As **análises da Steam** aparecem como informação, mas não decidem avisos: o jogo já está na sua lista de desejos.
- **Biblioteca:** valor da sua coleção, quanto falta para completar cada jogo com as DLCs, séries, coleção e **DLCs em promoção** (as que faltam nos seus jogos e estão com desconto agora).
- **Carrinho:** simule uma compra (jogos e bundles), escolha a loja de cada item e veja o total.
- **Configurações:** lojas, **O que te avisa** (Selo Kurokami ligado; Novo recorde, Igual ao recorde e Menor em 2 anos você liga se quiser, cada um com quantos avisos costuma dar por semana), desconto mínimo, keyshops, tipos de DLC, notificações e acesso pelo celular. Ligar um tipo não enche a tela de avisos: chega um resumo e, daí em diante, só os próximos.

### Pelo celular

Em **Configurações → Acesso pelo celular**, ligue a opção. Aparece um endereço (ex.: `http://192.168.0.10/kurokami`), um QR code e um **PIN**. No celular, no mesmo Wi-Fi, abra o endereço e digite o PIN uma vez. Se o Windows perguntar sobre o firewall, permita em **Redes privadas**.

---

## 5. Problemas comuns

| Problema | O que fazer |
|---|---|
| A notificação não aparece | *Configurações do Windows → Sistema → Notificações*: deixe ativado e desligue o *Não incomodar*. |
| "Lista de desejos vazia" | Deixe *Detalhes dos jogos* como **Público** na privacidade da Steam. |
| Chave recusada | Copie de novo; na IsThereAnyDeal use o campo **API Key**. |
| O painel não abre | Clique com o direito no ícone → **Reiniciar**. Se não houver ícone, abra o *Kurokami Radar* pelo menu Iniciar. |
| Quero ver o que aconteceu | Ícone → **Ver log**. |

## 6. Atualizar

O Radar procura versão nova **sempre que abre** e uma vez por dia enquanto fica aberto. Quando tem, chega uma notificação e aparece uma faixa verde no painel com **Atualizar agora**: ele baixa, instala por cima e abre de novo sozinho. Seus dados e chaves ficam.

Se preferir na mão: menu Iniciar → **Kurokami Radar (Atualizar)**, ou ícone → **Procurar atualização…**

## 7. Desinstalar

*Configurações do Windows → Aplicativos → Aplicativos instalados → Kurokami Radar → Desinstalar*. Os seus dados ficam em `%LOCALAPPDATA%\Kurokami Radar`; apague essa pasta se quiser remover tudo. As chaves ficam em *Gerenciador de Credenciais → Credenciais do Windows → Kurokami Radar*.

---

Detalhes técnicos (rodar pelo código, gerar o instalador, `config.json`): veja [TECNICO.md](TECNICO.md).
Preços via [IsThereAnyDeal](https://isthereanydeal.com), [GG.deals](https://gg.deals) e Steam.
