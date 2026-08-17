@echo off
setlocal
cd /d "%~dp0"

set "GIT_EXE=git"
where git >nul 2>nul
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "GIT_EXE=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
    ) else (
        echo ERRO: Git nao encontrado.
        echo Instale o Git for Windows e abra este arquivo novamente.
        pause
        exit /b 1
    )
)

if not exist ".git" (
    echo ERRO: esta pasta ainda nao esta conectada a um repositorio GitHub.
    echo Consulte a secao "Primeira publicacao" do README.md.
    pause
    exit /b 1
)

if not exist "outputs\dashboard_snapshot.pkl.gz" (
    echo ERRO: snapshot nao encontrado. Execute Run All em analise_rotas.ipynb.
    pause
    exit /b 1
)

if not exist "outputs\Comparativo_Rotas_VV.xlsx" (
    echo ERRO: relatorio Excel nao encontrado. Execute Run All em analise_rotas.ipynb.
    pause
    exit /b 1
)

"%GIT_EXE%" add -- ".gitignore" ".streamlit/config.toml" "README.md" "app.py" "route_analysis.py" "requirements.txt" "configurar_github.bat" "publicar_dashboard.bat" "assets/Logo Engelmig.jpg" "outputs/dashboard_snapshot.pkl.gz" "outputs/Comparativo_Rotas_VV.xlsx"
if errorlevel 1 goto falha

"%GIT_EXE%" diff --cached --quiet
if not errorlevel 1 (
    echo Nenhuma alteracao nova para publicar.
    pause
    exit /b 0
)

set "MENSAGEM=Atualiza dashboard de roteirizacao"
if not "%~1"=="" set "MENSAGEM=%~1"

"%GIT_EXE%" commit -m "%MENSAGEM%"
if errorlevel 1 goto falha

"%GIT_EXE%" push
if errorlevel 1 goto falha

echo.
echo Publicacao enviada ao GitHub.
echo O Streamlit Community Cloud iniciara a atualizacao automaticamente.
pause
exit /b 0

:falha
echo.
echo ERRO: nao foi possivel publicar a atualizacao.
echo Revise a mensagem do Git exibida acima.
pause
exit /b 1
