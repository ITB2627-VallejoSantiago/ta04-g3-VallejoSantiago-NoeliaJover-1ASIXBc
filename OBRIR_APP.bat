@echo off
title OBSERVATORI D'INCIDÈNCIES // CYBER-CORE v4.2
chcp 65001 > nul
cd /d "%~dp0"
python interfaz_incidencies.py
if errorlevel 1 (
    echo.
    echo Hi ha hagut un error en obrir l'aplicacio.
    pause
)
