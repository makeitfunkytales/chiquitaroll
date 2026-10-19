import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from sistemas.banco import inicializar_banco

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN não foi encontrado no arquivo .env")

class BotColecao(commands.Bot):
    async def setup_hook(self):
        inicializar_banco()
        await self.load_extension("comandos.colecao")
        await self.load_extension("comandos.trocas")
        await self.tree.sync()
        print("Comandos de barra sincronizados.")

intents = discord.Intents.default()
bot = BotColecao(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}.")

bot.run(DISCORD_TOKEN)
