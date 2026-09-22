@echo off
rem  Wrangle — lance le serveur de plateau et ouvre la page.
rem  Laissez cette fenetre ouverte pendant le tournage : c'est elle qui
rem  partage les saisies entre les appareils.
title Wrangle - serveur de plateau
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 serveur.py --ouvrir %*
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python serveur.py --ouvrir %*
  ) else (
    echo.
    echo  Python 3 est introuvable. Installez-le depuis https://www.python.org/downloads/
    echo  en cochant "Add python.exe to PATH", puis relancez ce fichier.
    echo.
  )
)
echo.
pause
