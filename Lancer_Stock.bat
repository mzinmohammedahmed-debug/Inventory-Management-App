@echo off
:: 1. On se place dans le dossier où se trouve ce fichier
cd /d "%~dp0"

:: 2. On active l'environnement virtuel (la bulle)
call .venv\Scripts\activate.bat

:: 3. On lance Streamlit
echo Lancement du logiciel de stock...
streamlit run "app.py"

:: 4. Pause pour lire les erreurs si ça plante
pause