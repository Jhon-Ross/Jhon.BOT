# Jhon.BOT 🤖

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-5865F2?style=for-the-badge&logo=discord)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow?style=for-the-badge)

Bem-vindo ao repositório do **Jhon.BOT**! 🚀
Este é um bot multifuncional e modular, desenvolvido para automatizar, moderar e trazer entretenimento para servidores do Discord com uma arquitetura moderna e escalável.

## 📋 Sobre o Projeto

O **Jhon.BOT** evoluiu para uma estrutura baseada em **Cogs**, facilitando a manutenção e adição de novas funcionalidades. Ele oferece uma gestão completa de comunidades, unindo economia, música e um sistema de moderação robusto e educativo.

Ele é ideal para servidores que buscam:
*   **Automação Avançada:** Gestão de cargos, verificação inteligente e boas-vindas.
*   **Moderação Educativa:** Sistema de avisos progressivos, anti-spam e anti-raid.
*   **Economia e Jogos:** Sistema de moedas (Pulerins) e Minigames (Blackjack).
*   **Engajamento:** Música de alta qualidade e comandos interativos.

## ✨ Funcionalidades Principais

*   🛡️ **Moderação Inteligente:**
    *   **Avisos Progressivos:** Sistema de Warns com punições automáticas (Timeout no 3º aviso).
    *   **Anti-Spam & Anti-Caps:** Monitoramento em tempo real para manter o chat limpo.
    *   **Anti-Raid & Anti-Fake:** Detecção de entrada em massa e proteção contra contas novas.
    *   **Logs de Auditoria:** Canal dedicado para registrar todas as ações administrativas.
*   ✅ **Sistema de Verificação:** Painel interativo com suporte a imagens locais (GIFs) e restrição por canal.
*   🎵 **Música (YouTube):** Sistema de áudio estável com suporte a filas e comandos de controle.
*   � **Economia & Jogos:** Ganhe Pulerins, aposte no Blackjack e acompanhe o Rank do servidor.
*   📜 **Comando de Regras:** `/regras` dinâmico que lê diretamente de um arquivo Markdown.
*   📖 **Versículo Diário:** Integração com API bíblica para mensagens inspiracionais.
*   💸 **Doações Pix:** Geração automática de QR Code para apoiar o projeto.

## 🚀 Como Iniciar

### Pré-requisitos
*   Python 3.8 ou superior instalado.
*   FFmpeg instalado e configurado no PATH (essencial para música).
*   Token do Discord Bot e variáveis configuradas no arquivo `.env`.

### Instalação Rápida (Windows)

O projeto conta com um script automatizado para facilitar a configuração inicial!

1.  Clone este repositório.
2.  Configure o arquivo `.env` dentro da pasta `bot-jhon` (veja a documentação para os campos necessários).
3.  Execute o arquivo **`start.bat`** na raiz do projeto.
    *   Ele criará o ambiente virtual (`venv`) automaticamente.
    *   Instalará todas as dependências do `requirements.txt`.
    *   Iniciará o bot com logs organizados.

## 📚 Documentação Completa

Para detalhes técnicos profundos sobre a arquitetura de **Cogs**, estrutura do banco de dados SQLite, lista completa de Slash Commands e guias de configuração, consulte nossa documentação oficial:

👉 **[Leia a Documentação Completa (Docs/bot-jhon.md)](Docs/bot-jhon.md)**

---
<div align="center">
  Desenvolvido com ❤️ por Jhon Ross
</div>
