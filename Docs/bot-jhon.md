# Bot Discord – Jhon.BOT 🤖

Documentação atualizada refletindo a transição para uma arquitetura modular baseada em **Cogs**, integração com banco de dados SQLite e sistema de moderação avançado.

## Parte 1 — Visão Geral e Funcionalidades

### 🎯 Objetivo
Automatizar a gestão e interação de servidores Discord, oferecendo ferramentas de moderação inteligente, economia, entretenimento e utilitários em uma única interface amigável.

### 🛡️ Sistema de Moderação (Moderacao Cog)
O bot utiliza uma abordagem educativa antes de aplicar punições severas:
- **Warns Progressivos:** 
  - 1º e 2º: Notificação via DM.
  - 3º: **Timeout automático** de 10 minutos.
  - 5º: Alerta para a Staff para avaliação de banimento.
- **Filtros Automáticos (Anti-Spam):**
  - Detecção de mensagens repetidas (flood).
  - Bloqueio de CAPS LOCK excessivo.
  - Limite de emojis por mensagem.
  - Filtro de links (permitidos apenas em canais específicos).
- **Segurança Ativa:**
  - **Anti-Fake:** Sinaliza contas criadas há menos de 7 dias.
  - **Anti-Raid:** Monitora bursts de entrada de membros em curto espaço de tempo.
- **Auditoria:** Logs detalhados em canal privado e limite diário de ações por staffer (Controle de Autoridade).

### 💰 Economia e Diversão (Economy Cog)
- **Pulerins:** Moeda virtual do servidor.
- **Blackjack:** Jogo de cassino totalmente interativo.
- **Rank:** Ranking dos membros mais ricos.

### 🛠️ Utilitários e Automação (Utils Cog)
- **Verificação:** Painel com botão persistente e suporte a GIFs locais.
- **Regras:** Comando `/regras` que exibe o conteúdo do arquivo `REGRAS_MODERACAO.md`.
- **Bíblia:** Versículos aleatórios via API externa.
- **Pix:** Geração de QR Code para doações.

---

## Parte 2 — Arquitetura Técnica

### 📂 Estrutura de Arquivos
- `main.py`: Ponto de entrada, configuração de intents e carregamento de Cogs.
- `database.py`: Interface com SQLite (gerenciamento de usuários, warnings e logs).
- `cogs/`:
  - `moderation.py`: Lógica de filtros, avisos e segurança.
  - `utils.py`: Comandos utilitários e painéis interativos.
  - `economy.py`: Sistema de moedas e ranking.
  - `events.py`: Listeners globais (boas-vindas, logs de voz, etc.).
  - `ai.py`: Integração com inteligência artificial.
  - `music.py`: Gerenciamento de áudio e filas do YouTube.

### 🗄️ Banco de Dados (SQLite)
Utiliza o arquivo `economy.db` com as seguintes tabelas principais:
- `users`: Armazena `user_id`, `pulerins` e `chips`.
- `warnings`: Registra `user_id`, `staff_id`, `reason` e `timestamp`.
- `mod_logs`: Auditoria de todas as ações (`warn`, `timeout`, `clear_warns`).

### ⚙️ Configuração (`.env`)
Campos obrigatórios:
- `DISCORD_TOKEN`: Token do bot.
- `GUILD_ID`: ID do servidor principal (para sincronização instantânea de comandos).
- `VERIFICAR_ID`: ID do canal de verificação.
- `CANAL_LOG_ID`: ID do canal de logs da Staff.
- `API_KEY` & `BIBLE_ID`: Credenciais para a API da Bíblia.
- IDs de cargos: `VISITANTE_ID`, `COMUNIDADE_ID`.

### 🚀 Sincronização de Comandos
O bot utiliza um sistema de sincronização otimizado em `main.py`:
- Durante o desenvolvimento, os comandos são sincronizados **instantaneamente** na guilda definida pelo `GUILD_ID` usando `tree.copy_global_to`.
- Comandos globais são limpos para evitar duplicação na interface do usuário.

---

## Parte 3 — Guia de Manutenção e Evolução

### Como Adicionar Novos Comandos
1. Crie ou edite um arquivo dentro da pasta `cogs/`.
2. Utilize o decorator `@app_commands.command()` para comandos Slash.
3. Adicione o nome da extensão na lista `initial_extensions` em `main.py`.

### Dependências Críticas
- `discord.py`: Framework principal.
- `yt-dlp` & `PyNaCl`: Essenciais para o sistema de música.
- `qrcode`: Geração de QR Codes Pix.
- `ffmpeg`: Necessário instalado no SO para processamento de áudio.

---
*Documentação atualizada em: 2026*
