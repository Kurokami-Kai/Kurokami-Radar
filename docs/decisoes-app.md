# Decisões: app, instalador e Windows

Leia antes de mexer em instalador, `.exe`, atualização, notificações ou na coleta da Steam inteira (spec 07).

- Gravações do painel competem com a coleta pelo SQLite: `timeout=30` e o carrinho em **arquivo próprio**.
- Atualizar arquivos com o Hunter aberto deixa o processo velho servindo a página nova (404 nas rotas novas). O painel compara `VERSAO_PAGINA` (no HTML) com a versão do servidor e avisa. **Sempre atualizar os dois juntos.**
- **0.12 → 0.13:** a 0.12 nunca gravou `meta.ult_completa`, então a primeira abertura depois de atualizar faz uma **verificação completa (30 a 40 min)**. Esperado, não é bug.
- `getpass` no Windows não aceita colar → chaves entram por janela Tk.
- Instalado não pode gravar na própria pasta → dados em `%LOCALAPPDATA%` e migração única de `C:\Kurokami Radar`.
- Toasts: XML montado com escape + `-EncodedCommand`; o `$` de "R$" quebrava a interpolação do PowerShell.
- **Sem ponte do Tampermonkey (removida na 0.16, pedido do dono: era remendo).** O navegador não deixa `localhost` usar a sessão da Steam; o carrinho vai pela extensão própria do Hunter (abaixo). Adicionar à lista de desejos pelo painel saiu junto (dependia da ponte).

- **Steam inteira (spec 07):** `IStoreQueryService/Query` exige `sort: 2` (sem ele a paginação repete e pula itens). Peça gzip (`rede.http_json` já pede): sem ele são 1,5 MB por página (126 MB numa grande promoção). Coleta incompleta não troca o retrato. Cada coleta substitui o retrato; a cada hora e no "Verificar agora", **logo depois das listas** (no fim ela esperava 7 min atrás do catálogo). Avisos continuam só para a lista (a Steam inteira daria centenas por dia).
- **Recordes da Steam inteira (08/10, noite; o dono pediu Selo e histórico também fora da lista):** marca da ITAD em lote (`prices/v3`, oferta da Steam: N novo recorde, H igual) para todos, guardada e só repedida quando o preço muda ou passou 1 dia; histórico (`history/v2`) só de quem está perto do recorde, 60 por rodada, e com ele a avaliação é a mesma da lista. **A ITAD tem cota de ~100 chamadas a cada 5 min:** no primeiro 429 o histórico para (sem esperar) e segue na próxima rodada; mapeamento e marcas no máximo 20 lotes por rodada (a lista usa a ITAD logo depois). A marca sem histórico é das lojas da ITAD (todas), não só das marcadas: é provisória.
- **A SteamDB mostra mais promoções que existem** quando a fila de atualização dela está cheia (aviso amarelo): em 08/10, 40.046 contra 6.905 da Steam; os de fora já tinham voltado ao preço cheio. Não comparar contagens com ela nesses dias.
