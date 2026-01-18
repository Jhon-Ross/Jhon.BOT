# Bot Discord – bot-jhon

Documentação dividida em duas partes: uma visão profissional para entendimento rápido e uma visão técnica para implementação, manutenção e evolução.

## Parte 1 — Leitura Profissional

- Objetivo
  - Automatizar interações em um servidor Discord: boas‑vindas, verificação de membros, comandos úteis, música e mensagens inspiracionais.
- Principais funcionalidades
  - Verificação por botão com atribuição automática de cargos.
  - Mensagem de boas‑vindas com embed e contagem de membros no tópico do canal.
  - Comandos: apresentação pessoal, lista de comandos, limpeza de mensagens, versículo bíblico aleatório.
  - Reprodução de música via YouTube com `yt_dlp` e `ffmpeg`.
  - Geração de QR Code Pix para doações.
  - Sistema de log de atividades em canal dedicado (entradas/saídas, voz, mensagens, reações, cargos).
- Experiência do usuário
  - Interação via comandos com prefixo `.` (ex.: `.ola`, `.limpar 10`).
  - Mensagens claras e responsivas (embeds com imagens e emojis).
  - Processo de verificação simples via botão “Iniciar verificação”.
- Requisitos para uso
  - Um servidor Discord com canais e cargos configurados (IDs no `.env`).
  - `DISCORD_TOKEN` válido e acesso às APIs externas quando aplicável.
- Como iniciar
  - Criar `.env` com os IDs e chaves.
  - Executar o arquivo `start.bat` na raiz do projeto (Recomendado).
  - Ou manualmente: instalar dependências e rodar `python bot-jhon/app.py`.

## Parte 2 — Leitura Técnica

- Stack e dependências
  - Python 3.x, `discord.py`, `python-dotenv`, `requests`, `qrcode[pil]`, `PyNaCl`, `asyncio` (em `bot-jhon/requirements.txt:1-6`).
  - `yt_dlp` é utilizado (bot-jhon/app.py:10), portanto deve ser instalado: `pip install yt_dlp`.
  - `ffmpeg` precisa estar instalado no sistema e acessível no PATH para áudio.
- Estrutura do projeto
  - `bot-jhon/app.py`: código principal do bot.
  - `bot-jhon/requirements.txt`: dependências Python.
  - `bot-jhon/.env`: variáveis de ambiente (não versionar segredos).
- Configuração de ambiente (`.env`)
  - `DISCORD_TOKEN`: token do bot no Discord.
  - `API_KEY`: chave da API Scripture (Bíblia).
  - `BIBLE_ID`: identificador da Bíblia na API.
  - `GUILD_ID`: ID do servidor.
  - `WELCOME_CHANNEL_ID`, `RULES_CHANNEL_ID`, `VERIFICAR_ID`, `CANAL_LOG_ID`, `BOAS_VINDAS_ID`: IDs de canais usados.
  - `VISITANTE_ID`, `COMUNIDADE_ID`: IDs de cargos para fluxo de verificação.
  - Leitura e casting ocorrem no início (bot-jhon/app.py:16-29).
- Comandos disponíveis
  - `.ola`: cumprimenta o usuário (bot-jhon/app.py:404-408).
  - `.limpar [n]`: apaga entre 1 e 100 mensagens, requer permissão (bot-jhon/app.py:445-456).
  - `.palavra`: retorna dois versículos consecutivos aleatórios (bot-jhon/app.py:410-417). Usa `get_random_verse` (bot-jhon/app.py:305-375).
  - `.apresentação`: envia embed de apresentação (bot-jhon/app.py:421-443).
  - `.comandos`: lista comandos disponíveis com explicações (bot-jhon/app.py:379-399).
  - `.verificar`: publica embed com botão de verificação persistente (bot-jhon/app.py:168-182). O botão dispara `handle_verification` (bot-jhon/app.py:146-164).
  - `.pix`: gera QR Code Pix e link “copia e cola” (bot-jhon/app.py:274-300).
- Fluxos e eventos
  - `on_ready`: envia log de inicialização para canal configurado.
  - `on_member_join`: boas‑vindas com embed, atribui cargo visitante, atualiza contagem e registra log de entrada.
  - `on_member_remove`: atualiza contagem de membros e registra log de saída.
  - `on_interaction`: captura clique no botão de verificação e chama `handle_verification`.
  - `on_voice_state_update`: registra entrada, saída e troca de canal de voz.
  - `on_member_update`: registra cargos adicionados e removidos.
  - `on_message_delete` / `on_message_edit`: registra mensagens apagadas e editadas (ignorando bots).
  - `on_reaction_add` / `on_reaction_remove`: registra reações adicionadas/removidas em mensagens.
- Música via YouTube
  - Configura `yt_dlp` e `FFmpegPCMAudio` para extrair áudio e tocar em canal de voz (bot-jhon/app.py:84-97, 99-114).
  - Comando `.musica <url>` conecta ao canal do usuário e toca a faixa (bot-jhon/app.py:116-142).
  - Requer `PyNaCl` e `ffmpeg` instalados; trata `TimeoutError` e `ClientException`.
- Integração Bíblia (Scripture API)
  - Busca livros, capítulos e dois versículos consecutivos, limpando HTML com regex (bot-jhon/app.py:305-370).
  - Trata indisponibilidade (HTTP 503) e erros de rede (bot-jhon/app.py:371-375).
- Doações Pix
  - Gera QR Code em memória com `qrcode` e envia arquivo junto ao embed (bot-jhon/app.py:280-300).
  - Inclui link “Pix Copia e Cola” para facilitar pagamento (bot-jhon/app.py:287-295).
- Boas‑vindas e contagem de membros
  - Atualiza o tópico do canal com contagem em emojis (bot-jhon/app.py:198-210). Usa `get_emoji_for_number` (bot-jhon/app.py:189-194).
- Logging e tratamento de erros
  - `logging.basicConfig(level=logging.INFO)` para console (bot-jhon/app.py:184).
  - `send_log_message` centraliza o envio de eventos para o canal `CANAL_LOG_ID`.
  - `on_command_error` ignora “Unknown message” e reloga outros.
- Observações técnicas e melhorias sugeridas
  - Adicionar `yt_dlp` ao `requirements.txt` para evitar falhas em produção.
  - Remover a duplicação de `on_interaction` mantendo apenas uma definição.
  - Considerar validação de IDs do `.env` na inicialização com mensagens de diagnóstico.
  - Externalizar URLs/imagens estáticas para configuração.
- Execução local
  - **Método Fácil (Recomendado):**
    - Basta dar dois cliques no arquivo `start.bat`. Ele cria o ambiente virtual, instala tudo e roda o bot.
  - **Método Manual:**
    - Criar e ativar ambiente virtual (opcional):
      - Windows PowerShell: `python -m venv .venv && .venv\Scripts\Activate.ps1`
    - Instalar dependências: `pip install -r bot-jhon/requirements.txt && pip install yt_dlp`.
    - Configurar `.env` em `bot-jhon/.env` com as variáveis citadas.
    - Rodar: `python bot-jhon/app.py`.
- Testes e validação
  - Testes manuais no servidor de desenvolvimento: verificar comandos, eventos e áudio.
  - Validar permissão do usuário para `.limpar` e respostas de erros.
  - Conferir disponibilidade da Scripture API e credenciais.
- Segurança
  - Nunca versionar valores de `DISCORD_TOKEN` e chaves.
  - Tratar cuidadosamente IDs de canais/cargos; evitar logs com dados sensíveis.

---

Esta documentação cobre visão executiva e um guia técnico completo para operar, manter e evoluir o projeto `bot-jhon` com referências diretas ao código.
