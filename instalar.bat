@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando dependencias do Kurokami Radar...
py -m pip install -r requirements.txt
if errorlevel 1 (echo Falhou. Confira se o Python esta instalado. & pause & exit /b 1)
echo.
py radar.py testar
echo.
echo Mandando uma notificacao de teste...
py radar.py testar-notificacao
echo.
set /p R=Abrir o Radar sozinho sempre que entrar no Windows? (S/N) 
if /i "%R%"=="S" py radar.py inicio instalar
echo.
echo Abrindo o Radar na bandeja (icone perto do relogio)...
start "" pyw radar.py bandeja
pause
