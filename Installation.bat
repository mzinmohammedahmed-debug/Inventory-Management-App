@echo off
setlocal
echo --- VERIFICATION / INSTALLATION DE PYTHON ---

:: 1. Vérifie si Python est déjà installé
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python est deja installe.
    goto :VENV
)

:: 2. Si Python est absent, tente l'installation via Winget
echo [INFO] Python n'est pas detecte. Tentative d'installation automatique...
winget install -e --id Python.Python.3.11 --scope machine --accept-package-agreements --accept-source-agreements

:: Vérification après tentative d'installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] L'installation automatique a echoue. 
    echo Veuillez installer Python manuellement sur https://www.python.org/
    echo N'oubliez pas de cocher "Add Python to PATH".
    pause
    exit /b
)

:VENV
:: 3. Création de l'environnement virtuel (.venv)
if not exist ".venv" (
    echo Creation de l'environnement virtuel...
    python -m venv .venv
)

:: 4. Installation des bibliothèques [cite: 53, 54]
echo Installation des composants (Streamlit, Pandas, OpenPyXL)... [cite: 53, 54]
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install streamlit pandas openpyxl [cite: 53, 54]

echo.
echo --- INSTALLATION TERMINEE ! --- [cite: 55]
echo Tu peux maintenant utiliser "Lancer_Stock.bat" [cite: 55]
pause