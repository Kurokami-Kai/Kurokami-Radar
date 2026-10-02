"""Iniciar com o Windows: tarefa agendada no logon; se o Windows recusar (sem admin),
um atalho na pasta Inicializar faz o mesmo papel."""
import os
import subprocess
import sys

from . import caminhos

TAREFA = "Kurokami Radar"


def comando():
    """(executavel, argumentos) que abre a bandeja sem janela de console."""
    if getattr(sys, "frozen", False):
        sem_janela = os.path.join(os.path.dirname(sys.executable), "KurokamiRadarBandeja.exe")
        return (sem_janela if os.path.isfile(sem_janela) else sys.executable), "bandeja"
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.isfile(pyw):
        pyw = sys.executable
    return pyw, '"%s" bandeja' % os.path.join(caminhos.BASE, "radar.py")


def _atalho():
    pasta = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.join(pasta, "Kurokami Radar.lnk")


def instalar():
    exe, args = comando()
    tr = '"%s" %s' % (exe, args)
    r = subprocess.run(["schtasks", "/Create", "/TN", TAREFA, "/TR", tr, "/SC", "ONLOGON", "/RL", "LIMITED", "/F"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "Tarefa agendada criada: o Radar abre sozinho quando você entrar no Windows."
    lnk = _atalho()
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');$s.TargetPath='%s';$s.Arguments='%s';"
          "$s.WorkingDirectory='%s';$s.Save()") % (lnk, exe, args.replace("'", "''"), caminhos.BASE)
    r2 = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if r2.returncode == 0:
        return ("O Windows nao deixou criar a tarefa agendada sem administrador (%s).\n"
                "Criei um atalho na pasta Inicializar, que faz o mesmo." % (r.stderr or r.stdout).strip())
    return "Nao consegui configurar a inicializacao:\n%s\n%s" % (r.stderr, r2.stderr)


def remover():
    subprocess.run(["schtasks", "/Delete", "/TN", TAREFA, "/F"], capture_output=True)
    if os.path.isfile(_atalho()):
        os.remove(_atalho())
    return "O Radar nao inicia mais sozinho com o Windows."
