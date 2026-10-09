; Instalador do Kurokami Hunter (Inno Setup 6). Gerado pelo GitHub Actions ou pelo gerar_setup.bat.
#define AppVer GetEnv("RADAR_VERSAO")
#if AppVer == ""
  #define AppVer "dev"
#endif

[Setup]
AppId={{16BB2CDB-31DC-438A-AD1A-8ECC6317BBD2}
AppName=Kurokami Hunter
AppVersion={#AppVer}
AppPublisher=Kurokami
AppPublisherURL=https://store.steampowered.com/
DefaultDirName={localappdata}\Programs\Kurokami Hunter
DefaultGroupName=Kurokami Hunter
DisableProgramGroupPage=yes
; o nome mudou na 0.17 (Kurokami Radar -> Kurokami Hunter): menu Iniciar na pasta nova, a antiga sai em [InstallDelete]
UsePreviousGroup=no
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=KurokamiRadar_Setup_v{#AppVer}
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=assets\radar.ico
UninstallDisplayIcon={app}\KurokamiRadar.exe
UninstallDisplayName=Kurokami Hunter
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "autostart"; Description: "Abrir o Kurokami Hunter junto com o Windows"
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "dist\KurokamiRadar\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; extensao do navegador (carrinho da Steam): o usuario a carrega uma vez em chrome://extensions
Source: "extensao\*"; DestDir: "{app}\extensao"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; atalhos de antes da troca de nome (a pasta, o exe e os dados continuam os mesmos)
Type: filesandordirs; Name: "{userprograms}\Kurokami Radar"
Type: files; Name: "{autodesktop}\Kurokami Radar.lnk"

[Icons]
Name: "{group}\Kurokami Hunter"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --abrir"
Name: "{group}\Perfil e chaves do Kurokami Hunter"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "chaves"
Name: "{group}\Kurokami Hunter (Atualizar)"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "atualizar-app"
Name: "{group}\Desinstalar o Kurokami Hunter"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kurokami Hunter"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --abrir"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Kurokami Radar"; ValueData: """{app}\KurokamiRadar.exe"" bandeja"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --esperar --abrir"; Description: "Abrir o Kurokami Hunter agora"; Flags: nowait postinstall skipifsilent
; atualizacao automatica (instalacao silenciosa): reabre o Kurokami Hunter sozinho
Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --esperar"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im KurokamiRadar.exe"; Flags: runhidden; RunOnceId: "FecharRadar"

[Code]
procedure Executar(Arq, Params: String);
var R: Integer;
begin
  Exec(Arq, Params, '', SW_HIDE, ewWaitUntilTerminated, R);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    { fecha o app instalado e a versao antiga que rodava pelo codigo (pythonw radar.py) }
    Executar(ExpandConstant('{cmd}'), '/c taskkill /f /im KurokamiRadar.exe');
    Executar('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like ''python*'' -and $_.CommandLine -like ''*radar.py*'' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"');
    { a versao pelo codigo abria por tarefa agendada/atalho: tira, para nao abrirem as duas }
    Executar(ExpandConstant('{cmd}'), '/c schtasks /Delete /TN "Kurokami Radar" /F');
    DeleteFile(ExpandConstant('{userstartup}\Kurokami Radar.lnk'));
  end;
end;
