# Sistema de coleção de personagens para Discord

## Requisitos
- Python 3.10 ou mais recente
- Um bot criado no Discord Developer Portal
- `discord.py` e `python-dotenv`

## Instalação no VSCodium / Windows PowerShell

1. Extraia a pasta do projeto.
2. Abra essa pasta no VSCodium.
3. No terminal, crie um ambiente virtual:
   ```powershell
   py -m venv .venv
   ```
4. Ative-o:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Se o PowerShell bloquear a ativação, use o terminal CMD e rode:
   ```cmd
   .venv\Scripts\activate.bat
   ```
5. Instale as dependências:
   ```powershell
   py -m pip install -r requirements.txt
   ```
6. Copie `.env.example` para um arquivo chamado `.env` e coloque seu token do Discord nele.
   **Não compartilhe o token e não envie o `.env` para o GitHub.**
7. No Discord Developer Portal, em Bot, ative **Message Content Intent** somente se outros recursos do seu bot precisarem dele. Este sistema de slash commands não depende desse intent.
8. Execute:
   ```powershell
   py main.py
   ```

## Como cadastrar personagens

### Pelo JSON
Edite `personagens.json` e execute `/importcharacters` no servidor. O comando exige a permissão **Manage Server / Gerenciar servidor**. Personagens já importados ou inválidos são ignorados.

Exemplo:
```json
[
  {
    "id": "personagem-unico",
    "nome": "Nome do personagem",
    "origem": "Nome da obra",
    "imagem": "https://site.com/imagem.png",
    "raridade": "rara"
  }
]
```

A imagem é opcional. Use um link direto de imagem acessível pelo Discord. Os IDs em `id` são identificadores externos e não são os IDs numéricos usados nos comandos.

### Pelo Discord
Use `/addcharacter` e preencha nome, origem, raridade e, opcionalmente, imagem e ID externo. Exige a permissão Gerenciar servidor.

Raridades aceitas: `comum`, `incomum`, `rara`, `epica`, `lendaria`.

## Comandos
- `/roll`: sorteia personagem ainda sem dono; botão de reivindicação dura 60 segundos.
- `/harem`: lista sua coleção e os IDs numéricos.
- `/personagem`: mostra detalhes e dono de um personagem.
- `/favorite`: alterna favorito de um personagem seu.
- `/favoritos`: lista favoritos.
- `/marry`: escolhe um personagem seu como casamento.
- `/trocar`: propõe troca usando IDs numéricos.
- `/aceitartroca`: aceita uma troca recebida.
- `/recusartroca`: recusa uma troca recebida.
- `/addcharacter`: cadastra personagem (Gerenciar servidor).
- `/importcharacters`: importa `personagens.json` (Gerenciar servidor).

## Observações
- O arquivo `colecao.db` é criado automaticamente na primeira execução. Faça cópias de segurança dele.
- Cada personagem só pode ter um dono de cada vez.
- A troca limpa favoritos e casamento dos dois personagens transferidos.
- Este é um projeto inicial: se quiser usar em muitos servidores ou com muitos usuários, vale adicionar paginação na coleção, expiração de propostas, logs e testes.
- Se seu bot já tem um `main.py`, não o substitua sem fazer backup. Integre os cogs `comandos.colecao` e `comandos.trocas` à estrutura existente e preserve os intents e eventos dos seus outros comandos.
