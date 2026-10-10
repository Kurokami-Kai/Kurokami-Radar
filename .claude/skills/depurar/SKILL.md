---
name: depurar
description: Roteiro para investigar bugs (evidência, hipótese, teste, correção pequena). Use quando o usuário relatar erro, print estranho, notificação ou preço errado, algo que "não puxou" ou travou.
---

# Depurar

Método geral: se a skill **`systematic-debugging`** (obra/superpowers) estiver instalada, siga as 4 fases dela (causa raiz antes de qualquer correção; 3 correções falhas = questionar a arquitetura). Esta skill só acrescenta **onde buscar evidência no Hunter**.

## 1. Evidência antes de código
Peça/colete só o necessário:
- `dados/radar.log` (últimas ~60 linhas) ou ícone → **Ver log**.
- O status/progresso do painel (`/api/resumo` → `progresso`, `ultima`).
- Para dado errado de um jogo: `py radar.py historico <jogo>`, `caminhos <jogo>`, `dlcs <jogo>`.
- Para formato de API: `py radar.py sondar <appid>` → `dados/sonda/sonda.json` (filtre com `python -c`, não abra inteiro).
- Versão rodando × versão dos arquivos (faixa vermelha no painel indica processo antigo).

## 2. Hipótese explícita
Escreva 1 a 3 causas prováveis e o que confirmaria cada uma. Confira `docs/decisoes.md`: muitos sintomas já têm causa conhecida (preço "grátis", fuso, pacote parcial, Hunter antigo servindo página nova…).

## 3. Reproduzir sem rede
Com uma cópia do banco do usuário (skill `testar-sem-rede`), chame a função suspeita direto e mostre o valor errado. Só então corrija.

## 4. Corrigir pequeno
- Uma causa por vez; mudança mínima.
- Se o usuário não pode te dar mais dados, acrescente **diagnóstico** (motivo no log/painel) junto da correção, para a próxima ocorrência explicar a si mesma.

## 5. Registrar
Bug com causa não óbvia → uma linha em `docs/decisoes.md` ("sintoma → causa → regra").
