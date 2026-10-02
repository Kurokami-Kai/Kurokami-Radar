; Instalador do Kurokami Radar (Inno Setup 6). Gerado pelo GitHub Actions ou pelo gerar_setup.bat.
#define AppVer GetEnv("RADAR_VERSAO")
#if AppVer == ""
  #define AppVer "dev"
#endif

[Setup]
AppId={{16BB2CDB-31DC-438A-AD1A-8ECC6317BBD2}
AppName=Kurokami Radar
AppVersion={#AppVer}
AppPublisher=Kurokami
AppPublisherURL=https://store.steampowered.com/
DefaultDirName={localappdata}\Programs\Kurokami Radar
DefaultGroupName=Kurokami Radar
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=KurokamiRadar_Setup_v{#AppVer}
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=assets\radar.ico
UninstallDisplayIcon={app}\KurokamiRadar.exe
UninstallDisplayName=Kurokami Radar
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "autostart"; Description: "Abrir o Radar junto com o Windows"
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "dist\KurokamiRadar\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Kurokami Radar"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --abrir"
Name: "{group}\Perfil e chaves do Kurokami Radar"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "chaves"
Name: "{group}\Desinstalar o Kurokami Radar"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kurokami Radar"; Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --abrir"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Kurokami Radar"; ValueData: """{app}\KurokamiRadar.exe"" bandeja"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\KurokamiRadar.exe"; Parameters: "bandeja --esperar --abrir"; Description: "Abrir o Kurokami Radar agora"; Flags: nowait postinstall skipifsilent

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
    { fecha o Radar instalado e a versao antiga que rodava pelo codigo (pythonw radar.py) }
    Executar(ExpandConstant('{cmd}'), '/c taskkill /f /im KurokamiRadar.exe');
    Executar('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like ''python*'' -and $_.CommandLine -like ''*radar.py*'' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"');
    { a versao pelo codigo abria por tarefa agendada/atalho: tira, para nao abrirem as duas }
    Executar(ExpandConstant('{cmd}'), '/c schtasks /Delete /TN "Kurokami Radar" /F');
    DeleteFile(ExpandConstant('{userstartup}\Kurokami Radar.lnk'));
  end;
end;
