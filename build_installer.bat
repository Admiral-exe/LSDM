@echo off
setlocal enabledelayedexpansion
title LSDM - Desktop App & Installer Builder
echo ======================================================================
echo           LSDM (Laboratory Sample & Dispatch Management)
echo                Automated Packaging & Release Pipeline
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Ensure Python Virtual Environment exists
if exist .venv\Scripts\python.exe (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    set "PYINSTALLER_EXE=.venv\Scripts\pyinstaller.exe"
) else (
    set "PYTHON_EXE=python"
    set "PYINSTALLER_EXE=pyinstaller"
)

:: 2. Extract Version from version.py
for /f "tokens=2 delims==" %%I in ('%PYTHON_EXE% -c "import version; print(version.__version__)"') do (
    set "APP_VERSION=%%I"
)
set "APP_VERSION=%APP_VERSION: =%"
if "%APP_VERSION%"=="" (
    set "APP_VERSION=1.0.0"
)
echo [*] Target Version: v%APP_VERSION%

:: 3. Generate Logo & Icon Assets
echo [*] Generating Logo & High-DPI Windows Icons...
%PYTHON_EXE% tools\generate_logo.py
if errorlevel 1 (
    echo [!] Failed to generate icons.
    pause
    exit /b 1
)

:: 4. Build LSDM.exe using PyInstaller
echo.
echo [*] Building Standalone LSDM.exe with PyInstaller...
%PYINSTALLER_EXE% lsdm.spec --clean --noconfirm
if errorlevel 1 (
    echo [!] PyInstaller build failed.
    pause
    exit /b 1
)

:: 5. Copy templates to distribution folder
copy /y APRIL_TEMPLATE.xlsx dist\LSDM\ >nul
copy /y MASTER_TEMPLATE.xlsx dist\LSDM\ >nul

:: 6. Locate Inno Setup Compiler
set "ISCC_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
) else (
    for %%X in (iscc.exe) do (set "ISCC_PATH=%%~$PATH:X")
)

if "%ISCC_PATH%"=="" (
    echo [!] Inno Setup Compiler (ISCC.exe) not found.
    echo     Please install Inno Setup 6 via: winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

:: 7. Compile Single-File Installer
echo.
echo [*] Compiling Single-File Setup Wizard using Inno Setup...
echo     Compiler: %ISCC_PATH%
"%ISCC_PATH%" /DMyAppVersion="%APP_VERSION%" installer.iss
if errorlevel 1 (
    echo [!] Inno Setup packaging failed.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo  SUCCESS: Installer Generated Successfully!
echo  Installer Location: dist_installer\LSDM_Setup_v%APP_VERSION%.exe
echo ======================================================================
echo.
pause
