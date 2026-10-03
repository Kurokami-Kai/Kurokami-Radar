@echo off
chcp 65001 >nul
title Exportar documentacao para o Projeto do claude.ai
cd /d "%~dp0.."
py tools\exportar_docs.py
echo.
pause
