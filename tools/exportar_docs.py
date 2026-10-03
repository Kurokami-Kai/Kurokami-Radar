"""Junta a documentacao do projeto numa pasta da Area de Trabalho para enviar ao Projeto do claude.ai.

Uso: dois cliques em tools\\exportar_docs.bat (ou: py tools/exportar_docs.py)

O que faz:
- copia CLAUDE.md, README.md, docs/*.md (menos referencia.md) e docs/specs/*.md para
  Area de Trabalho\\kurokami-docs\\todos   (o conjunto completo, sempre atualizado)
- compara com a exportacao anterior e coloca so o que e NOVO ou MUDOU em
  Area de Trabalho\\kurokami-docs\\enviar  (e so isso que precisa subir de novo)
- lista o que foi apagado do projeto (para voce remover tambem no claude.ai)
- abre a pasta no Explorador
- so registra a exportacao depois que voce confirma o envio: se nao confirmar (ou fechar a
  janela), a proxima exportacao mostra as mesmas mudancas de novo
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORAR = {"referencia.md"}  # lista de funcoes: util so para o Claude Code


def area_de_trabalho():
    """Pasta real da Area de Trabalho (inclusive quando o OneDrive a redireciona)."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0 and buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def arquivos():
    """{nome_no_destino: caminho_de_origem}"""
    out = {}
    for nome in ("CLAUDE.md", "README.md"):
        p = os.path.join(RAIZ, nome)
        if os.path.isfile(p):
            out[nome] = p
    docs = os.path.join(RAIZ, "docs")
    for nome in sorted(os.listdir(docs)) if os.path.isdir(docs) else []:
        if nome.endswith(".md") and nome not in IGNORAR:
            out["docs-" + nome] = os.path.join(docs, nome)
    specs = os.path.join(docs, "specs")
    for nome in sorted(os.listdir(specs)) if os.path.isdir(specs) else []:
        if nome.endswith(".md"):
            out["spec-" + nome] = os.path.join(specs, nome)
    return out


def hash_de(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def limpar(pasta):
    if os.path.isdir(pasta):
        shutil.rmtree(pasta)
    os.makedirs(pasta)


def main():
    base = os.path.join(area_de_trabalho(), "kurokami-docs")
    todos, enviar = os.path.join(base, "todos"), os.path.join(base, "enviar")
    manifesto = os.path.join(base, ".ultima_exportacao.json")
    os.makedirs(base, exist_ok=True)
    try:
        with open(manifesto, encoding="utf-8") as f:
            antes = json.load(f)
    except (OSError, ValueError):
        antes = {}

    atual = arquivos()
    if not atual:
        print("Nao achei a documentacao. Rode a partir da pasta do projeto.")
        return 1
    limpar(todos)
    limpar(enviar)
    novos, mudados, iguais, agora = [], [], [], {}
    for nome, origem in atual.items():
        h = hash_de(origem)
        agora[nome] = h
        shutil.copy2(origem, os.path.join(todos, nome))
        if nome not in antes:
            novos.append(nome)
        elif antes[nome] != h:
            mudados.append(nome)
        else:
            iguais.append(nome)
            continue
        shutil.copy2(origem, os.path.join(enviar, nome))
    apagados = sorted(set(antes) - set(agora))

    primeira = not antes
    print("Documentacao exportada para: %s" % base)
    print()
    if primeira:
        print("Primeira exportacao: envie TODOS os %d arquivos da pasta 'enviar' para o Projeto." % len(agora))
    elif not (novos or mudados or apagados):
        print("Nada mudou desde a ultima exportacao. Nao precisa enviar nada.")
    else:
        if novos:
            print("NOVOS (envie):        " + ", ".join(novos))
        if mudados:
            print("ALTERADOS (troque):   " + ", ".join(mudados))
        if apagados:
            print("APAGADOS (remova do Projeto): " + ", ".join(apagados))
        print("Iguais (nao mexa):    %d arquivo(s)" % len(iguais))
    print()
    print("No claude.ai: Projeto Kurokami Radar -> Contexto -> remova as versoes antigas dos")
    print("arquivos ALTERADOS/APAGADOS e envie tudo o que estiver na pasta 'enviar'.")
    pendente = primeira or novos or mudados or apagados
    if os.name == "nt" and (novos or mudados or primeira):
        subprocess.Popen(["explorer", enviar])
    if pendente:
        print()
        try:
            r = input("Depois de atualizar o Projeto, digite S e Enter (so Enter = ainda nao enviei): ")
        except EOFError:
            r = ""
        if r.strip().lower() != "s":
            print("Nao registrei: a proxima exportacao mostra estas mudancas de novo.")
            return 0
    with open(manifesto, "w", encoding="utf-8") as f:
        json.dump(agora, f, indent=1)
    if pendente:
        print("Exportacao registrada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
