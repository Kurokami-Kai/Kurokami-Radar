# Spec 02 — DLCs não aparecem (ex.: Civilization)

Status: **feito em v0.13.0** · Skill: `depurar` (+ `systematic-debugging`)

## Sintoma (dono, 02/10, depois da instalação limpa)
"O Civilization não mostrou DLCs. Nada mostrou DLCs direito."

## O que já se sabe
- Num banco anterior (01/10), *Sid Meier's Civilization VII* (appid 1295660) tinha **27 DLCs** na tabela `dlc`. Então o caminho funcionava antes da reinstalação.
- A lista de DLCs vem de: `GetDLCForApps` (bloqueado para chave comum → `meta.dlcforapps_bloqueado`) → **plano B** `steam.dlcs_pela_loja` (`appdetails?filters=basic`, ~1,6 s/jogo, orçamento `chamadas_lentas_por_rodada`, cache `consulta_lenta` tipo `dlcs`) → DLCs vistas em bundles/edições.
- A primeira verificação agora é completa (`sem_limite`), mas leva tempo; enquanto isso a biblioteca mostra "N jogos ainda sem lista de DLCs".

## Hipóteses (confirmar em ordem)
1. **A verificação completa ainda não terminou** ou foi interrompida (Radar fechado no meio). Evidência: `dados/radar.log` (procurar "usando a loja (plano B)" e "%d/%d"), `meta.ult_completa`, `SELECT COUNT(*) FROM consulta_lenta WHERE tipo='dlcs'`.
2. **Instalado (.exe) × caminho**: dados migrados ou não de `C:\Kurokami Radar` — conferir se o banco em `%LOCALAPPDATA%\Kurokami Radar\dados` tem `dlc` vazio.
3. **`appdetails` com `filters=basic` não trouxe o campo `dlc`** para alguns jogos (resposta muda por região/jogo). Evidência: `py radar.py sondar 289070 1295660` e olhar o JSON; testar a chamada sem `filters`.
4. **Ritmo da loja**: 429 em sequência derruba o plano B (log com "DLCs de X falharam").
5. **Exibição**: DLCs existem na tabela mas o painel filtra (classe ignorada, preço 0, `relevantes()`), ou a ficha usa `ctx.dlcs` de outro `appid` (Civ VI 289070 × Civ VII 1295660).

## Saída esperada
- Causa raiz com evidência, correção mínima e **diagnóstico permanente**: na ficha do jogo, quando não houver DLCs, mostrar o motivo ("lista ainda não consultada — fila em X/Y", "a Steam não informou DLCs", "consulta falhou em <data>").
- Registrar em `docs/decisoes.md`.

## Resultado
- Causa: a 0.12 limitava a 1ª verificação a 120 consultas de DLC por rodada; no banco do dono só 120 de 1256 jogos tinham lista às 19:56 de 02/10 e o resto só foi consultado entre 20:49 e 21:20 (Civ VII às 20:53, Civ VI às 21:09). Hipóteses 2 a 5 descartadas com o banco e o log.
- Correção: 1ª verificação completa (0.13); motivo na ficha (`dlcs_estado`); falha gravada como `dlcs_falha` sem contar como consultado.
