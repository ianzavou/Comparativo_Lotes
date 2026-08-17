@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "GIT_EXE=git"
where git >nul 2>nul
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "GIT_EXE=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
    ) else (
        echo ERRO: Git nao encontrado.
        pause
        exit /b 1
    )
)

if not exist ".git" (
    "!GIT_EXE!" init -b main
    if errorlevel 1 goto falha
)

"!GIT_EXE!" config user.name >nul 2>nul
if errorlevel 1 (
    set /p "GIT_NAME=Informe seu nome para o historico do Git: "
    if not defined GIT_NAME goto dados_incompletos
    "!GIT_EXE!" config user.name "!GIT_NAME!"
)

"!GIT_EXE!" config user.email >nul 2>nul
if errorlevel 1 (
    set /p "GIT_EMAIL=Informe o e-mail da sua conta GitHub: "
    if not defined GIT_EMAIL goto dados_incompletos
    "!GIT_EXE!" config user.email "!GIT_EMAIL!"
)

"!GIT_EXE!" add -- ".gitignore" ".streamlit/config.toml" "README.md" "app.py" "route_analysis.py" "requirements.txt" "configurar_github.bat" "publicar_dashboard.bat" "assets/Logo Engelmig.jpg" "outputs/dashboard_snapshot.pkl.gz" "outputs/Comparativo_Rotas_VV.xlsx"
if errorlevel 1 goto falha

"!GIT_EXE!" diff --cached --quiet
if errorlevel 1 (
    "!GIT_EXE!" commit -m "Prepara dashboard para Streamlit Community Cloud"
    if errorlevel 1 goto falha
)

"!GIT_EXE!" remote get-url origin >nul 2>nul
if errorlevel 1 (
    echo.
    echo Crie antes um repositorio PRIVADO e VAZIO no GitHub.
    set /p "REPO_URL=Cole a URL HTTPS do repositorio: "
    if not defined REPO_URL goto dados_incompletos
    "!GIT_EXE!" remote add origin "!REPO_URL!"
    if errorlevel 1 goto falha
)

echo.
echo Enviando a versao inicial. O Git Credential Manager podera abrir o navegador.
"!GIT_EXE!" push -u origin main
if errorlevel 1 goto falha

echo.
echo Projeto enviado ao GitHub com sucesso.
echo Agora crie o app privado em https://share.streamlit.io usando app.py.
pause
exit /b 0

:dados_incompletos
echo.
echo Configuracao cancelada porque uma informacao obrigatoria nao foi preenchida.
pause
exit /b 1

:falha
echo.
echo ERRO: a configuracao nao foi concluida. Revise a mensagem acima.
pause
exit /b 1
