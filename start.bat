@echo off
setlocal
cd /d "%~dp0"
title Bot Discord - Jhon Ross

:: ==========================================
:: CONFIGURACAO VISUAL E INICIALIZACAO
:: ==========================================
color 0B
:: cls removido a pedido do usuario
echo.
echo  ======================================================
echo          INICIANDO BOT - JHON ROSS
echo  ======================================================
echo.

:: ==========================================
:: ETAPA 1: VERIFICAR PASTA DO PROJETO
:: ==========================================
echo [INFO] Verificando diretorio do projeto...
if exist "bot-jhon" goto step_python
:: Se nao existir, erro fatal
color 0C
echo.
echo [ERRO CRITICO] A pasta 'bot-jhon' nao foi encontrada!
echo.
echo O script esta rodando em: "%CD%"
echo Esperava encontrar a pasta 'bot-jhon' aqui.
echo.
pause
exit /b

:step_python
:: ==========================================
:: ETAPA 2: ENTRAR NA PASTA E CHECAR PYTHON
:: ==========================================
cd bot-jhon
echo [INFO] Entrando na pasta 'bot-jhon'...

echo [INFO] Verificando instalacao global do Python...
python --version >nul 2>&1
if not errorlevel 1 goto step_venv

py --version >nul 2>&1
if not errorlevel 1 goto step_venv

color 0C
echo.
echo [ERRO CRITICO] Python nao encontrado!
echo Instale o Python em python.org e marque "Add to PATH".
echo.
pause
exit /b

:step_venv
:: ==========================================
:: ETAPA 3: AMBIENTE VIRTUAL (VENV)
:: ==========================================
:: Verifica se o executavel do python no venv existe
if exist "venv\Scripts\python.exe" goto step_install_deps

echo [INFO] Criando ambiente virtual (venv)...
python -m venv venv
if not errorlevel 1 goto step_install_deps

py -3 -m venv venv
if not errorlevel 1 goto step_install_deps

color 0C
echo.
echo [ERRO] Falha ao criar o ambiente virtual (venv).
pause
exit /b

:step_install_deps
:: ==========================================
:: ETAPA 4: INSTALAR DEPENDENCIAS (USANDO O PYTHON DO VENV EXPLICITAMENTE)
:: ==========================================
echo [INFO] Usando Python do VENV: "%CD%\venv\Scripts\python.exe"

:: Atualiza pip
".\venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1

echo [INFO] Verificando e instalando dependencias...
if exist "requirements.txt" (
    ".\venv\Scripts\python.exe" -m pip install -r requirements.txt
) else (
    echo [AVISO] requirements.txt nao encontrado. Instalando manualmente...
    ".\venv\Scripts\python.exe" -m pip install discord.py python-dotenv requests PyNaCl yt_dlp qrcode[pil]
)

:: Garante yt_dlp
".\venv\Scripts\python.exe" -m pip install yt_dlp >nul 2>&1

:: ==========================================
:: ETAPA 5: EXECUCAO DO BOT
:: ==========================================
:: cls removido
color 0A
echo.
echo  ======================================================
echo          TUDO PRONTO! INICIANDO O BOT...
echo  ======================================================
echo.
echo  [LOGS] Acompanhe abaixo as mensagens do sistema:
echo  ------------------------------------------------------

:: Executa usando explicitamente o python do venv
".\venv\Scripts\python.exe" app.py

:: ==========================================
:: TRATAMENTO DE ERRO DE EXECUCAO
:: ==========================================
if errorlevel 1 goto runtime_error

echo.
echo [INFO] O bot foi encerrado normalmente.
pause >nul
exit /b

:runtime_error
color 0C
echo.
echo  ======================================================
echo          OPS! O BOT PAROU COM UM ERRO
echo  ======================================================
echo.
echo  [DIAGNOSTICO]
echo  1. Leia as mensagens de erro acima.
echo  2. Verifique o arquivo .env
echo.
echo  Pressione qualquer tecla para tentar reiniciar...
pause
goto step_python