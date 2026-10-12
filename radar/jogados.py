"""Aba Status > Progresso: o que voce realmente jogou. Junta o tempo jogado (tempo_jogo, do GetOwnedGames) com as
conquistas de cada jogo (conquista_jogo, coletadas aos poucos pela pista lenta).

Estado de cada jogo (nunca DLC):
  platina   todas as conquistas feitas
  andamento algumas feitas
  zero      tem conquistas, nenhuma feita e mais de 4 h: NAO conta como jogado (quem joga 4 h pega alguma; provavel
            farm de cartas / jogo aberto parado)
  sem       o jogo nao tem conquistas e passa de 4 h: tambem NAO conta (mesma razao)
  pouco     ate 4 h e nenhuma conquista feita (tenha o jogo conquistas ou nao): conta como jogado (so experimentou)
  nunca     0 minutos
  pendente  jogado, mas as conquistas ainda nao foram consultadas (ou a consulta falhou)"""


LIMITE_SEM_CONQUISTA = 240   # minutos: acima disso, sem nenhuma conquista feita, o jogo nao conta como jogado


def estado(minutos, feitas, total):
    if not minutos:
        return "nunca"
    if total is None or total < 0:
        return "pendente"
    if total > 0 and feitas >= total:
        return "platina"
    if feitas > 0:
        return "andamento"
    if minutos <= LIMITE_SEM_CONQUISTA:
        return "pouco"
    return "sem" if total == 0 else "zero"


def resumo(b):
    linhas = b.q("""SELECT t.appid, j.nome, j.capa, t.minutos, t.ultima, c.feitas, c.total
                    FROM tempo_jogo t JOIN jogo j ON j.appid=t.appid AND j.possuido=1
                    LEFT JOIN conquista_jogo c ON c.appid=t.appid
                    WHERE j.nome IS NOT NULL AND (j.tipo IS NULL OR j.tipo='jogo')""")
    jogos = [{"appid": r["appid"], "nome": r["nome"], "capa": r["capa"], "minutos": r["minutos"] or 0, "ultima": r["ultima"],
              "feitas": r["feitas"] or 0, "total": max(r["total"] or 0, 0),
              "estado": estado(r["minutos"], r["feitas"] or 0, r["total"])} for r in linhas]
    # pendentes: ainda nao consultados (consulta que falhou, total -1, tambem aparece como "pendente", mas nao no aviso)
    return {"jogos": jogos, "pendentes": sum(1 for r, j in zip(linhas, jogos) if j["estado"] == "pendente" and r["total"] is None)}
