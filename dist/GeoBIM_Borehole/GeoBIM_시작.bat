@echo off
chcp 65001 >nul
title GeoBIM
cd /d "%~dp0"
if exist "%~dp0jdk_folderin\java.exe" (
    set JAVA_HOME=%~dp0jdk_folder
    set PATH=%~dp0jdk_folderin;%PATH%
)
start "" GeoBIM_Borehole.exe
