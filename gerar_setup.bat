@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Gera o instalador KurokamiRadar_Setup.exe neste PC.
echo Precisa: Python (ja tem) e Inno Setup 6 (https://jrsoftware.org/isdl.php).
echo.
for /f "tokens=2 delims==" %%v in ('findstr /c:"VERSAO = " radar\__init__.py') do set RAW=%%v
set RADAR_VERSAO=%RAW:"=%
set RADAR_VERSAO=%RADAR_VERSAO: =%
echo Versao: %RADAR_VERSAO%
py -m pip install -q -r requirements.txt pyinstaller || goto erro
py tools\gerar_icone.py || goto erro
py -m PyInstaller --noconfirm --clean --onedir --windowed --name KurokamiRadar --icon assets\radar.ico --add-data "radar\painel.html;radar" --add-data "radar\ofertas.html;radar" --add-data "radar\biblioteca.html;radar" --collect-submodules radar --collect-submodules keyring --collect-submodules pystray --hidden-import win32ctypes.core --hidden-import win32ctypes.pywin32 radar.py || goto erro
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (echo Inno Setup 6 nao encontrado. Instale e rode de novo. & start "" https://jrsoftware.org/isdl.php & pause & exit /b 1)
"%ISCC%" installer.iss || goto erro
echo.
echo Pronto: output\KurokamiRadar_Setup_v%RADAR_VERSAO%.exe
explorer output
pause
exit /b 0
:erro
echo Falhou. Veja a mensagem acima.
pause
exit /b 1
