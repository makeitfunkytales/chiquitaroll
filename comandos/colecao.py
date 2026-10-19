import json
import random
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from sistemas.banco import conectar

RARIDADES = {"comum", "incomum", "rara", "epica", "lendaria"}
RARIDADE_EMOJI = {
    "comum": "⚪",
    "incomum": "🟢",
    "rara": "🔵",
    "epica": "🟣",
    "lendaria": "🟡",
}

def buscar_personagem(character_id):
    with conectar() as db:
        return db.execute(
            "SELECT * FROM characters WHERE id = ?", (character_id,)
        ).fetchone()

def personagem_do_usuario(character_id, user_id):
    with conectar() as db:
        return db.execute(
            """SELECT c.*, uc.owner_id, uc.favorite, uc.married
               FROM characters c
               JOIN user_characters uc ON uc.character_id = c.id
               WHERE c.id = ? AND uc.owner_id = ?""",
            (character_id, str(user_id)),
        ).fetchone()

def criar_embed(personagem, descricao=None):
    raridade = personagem["rarity"]
    embed = discord.Embed(
        title=f"{RARIDADE_EMOJI.get(raridade, '')} {personagem['name']}",
        description=descricao or f"**Origem:** {personagem['origin']}\n**Raridade:** {raridade.title()}\n**ID:** `{personagem['id']}`",
        color=discord.Color.blurple(),
    )
    if personagem["image_url"] and personagem["image_url"].startswith(("https://", "http://")):
        embed.set_image(url=personagem["image_url"])
    return embed

class ReivindicarView(discord.ui.View):
    def __init__(self, character_id):
        super().__init__(timeout=60)
        self.character_id = character_id

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="💗")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        try:
            with conectar() as db:
                db.execute("BEGIN IMMEDIATE")
                dono = db.execute(
                    "SELECT owner_id FROM user_characters WHERE character_id = ?",
                    (self.character_id,),
                ).fetchone()
                if dono:
                    db.rollback()
                    button.disabled = True
                    await interaction.response.edit_message(
                        content="Alguém chegou primeiro. Esse personagem já tem dono.",
                        view=self,
                    )
                    return
                db.execute(
                    "INSERT INTO user_characters(character_id, owner_id) VALUES (?, ?)",
                    (self.character_id, user_id),
                )
                personagem = db.execute(
                    "SELECT * FROM characters WHERE id = ?", (self.character_id,)
                ).fetchone()
                db.commit()
        except Exception:
            await interaction.response.send_message(
                "Não consegui concluir a reivindicação. Tente novamente.",
                ephemeral=True,
            )
            return

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"{interaction.user.mention} ficou com **{personagem['name']}**!",
            view=self,
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class Colecao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Sorteia um personagem para reivindicar.")
    async def roll(self, interaction: discord.Interaction):
        with conectar() as db:
            personagem = db.execute("""
                SELECT c.* FROM characters c
                LEFT JOIN user_characters uc ON uc.character_id = c.id
                WHERE uc.character_id IS NULL
                ORDER BY RANDOM() LIMIT 1
            """).fetchone()

        if not personagem:
            await interaction.response.send_message(
                "Não há personagens livres no momento. Adicione mais personagens ou aguarde uma troca.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=criar_embed(personagem, "Clique no botão para reivindicar este personagem. Você tem 60 segundos."),
            view=ReivindicarView(personagem["id"]),
        )

    @app_commands.command(name="harem", description="Mostra os personagens que você possui.")
    async def harem(self, interaction: discord.Interaction):
        with conectar() as db:
            personagens = db.execute("""
                SELECT c.id, c.name, c.origin, c.rarity, uc.favorite, uc.married
                FROM user_characters uc
                JOIN characters c ON c.id = uc.character_id
                WHERE uc.owner_id = ?
                ORDER BY c.name COLLATE NOCASE
            """, (str(interaction.user.id),)).fetchall()

        if not personagens:
            await interaction.response.send_message(
                "Sua coleção está vazia. Use `/roll` para tentar conseguir um personagem.",
                ephemeral=True,
            )
            return

        linhas = []
        for p in personagens[:40]:
            marcas = []
            if p["favorite"]:
                marcas.append("★ favorito")
            if p["married"]:
                marcas.append("♡ casamento")
            extra = f" — {'; '.join(marcas)}" if marcas else ""
            linhas.append(f"`{p['id']}` **{p['name']}** — {p['origin']} ({p['rarity']}){extra}")

        embed = discord.Embed(
            title=f"Coleção de {interaction.user.display_name}",
            description="\n".join(linhas),
            color=discord.Color.blurple(),
        )
        if len(personagens) > 40:
            embed.set_footer(text=f"Mostrando 40 de {len(personagens)} personagens.")
        else:
            embed.set_footer(text=f"Total: {len(personagens)} personagem(ns).")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="favorite", description="Marca ou desmarca um personagem como favorito.")
    @app_commands.describe(personagem_id="ID mostrado em /harem")
    async def favorite(self, interaction: discord.Interaction, personagem_id: int):
        with conectar() as db:
            owned = db.execute(
                "SELECT favorite FROM user_characters WHERE character_id = ? AND owner_id = ?",
                (personagem_id, str(interaction.user.id)),
            ).fetchone()
            if not owned:
                await interaction.response.send_message(
                    "Você não possui esse personagem. Confira o ID em `/harem`.",
                    ephemeral=True,
                )
                return
            novo_valor = 0 if owned["favorite"] else 1
            db.execute(
                "UPDATE user_characters SET favorite = ? WHERE character_id = ? AND owner_id = ?",
                (novo_valor, personagem_id, str(interaction.user.id)),
            )
        texto = "adicionado aos" if novo_valor else "removido dos"
        await interaction.response.send_message(
            f"Personagem {texto} favoritos.", ephemeral=True
        )

    @app_commands.command(name="favoritos", description="Lista seus personagens favoritos.")
    async def favoritos(self, interaction: discord.Interaction):
        with conectar() as db:
            rows = db.execute("""
                SELECT c.id, c.name, c.origin, c.rarity
                FROM user_characters uc
                JOIN characters c ON c.id = uc.character_id
                WHERE uc.owner_id = ? AND uc.favorite = 1
                ORDER BY c.name COLLATE NOCASE
            """, (str(interaction.user.id),)).fetchall()

        if not rows:
            await interaction.response.send_message(
                "Você ainda não marcou favoritos. Use `/favorite`.",
                ephemeral=True,
            )
            return
        texto = "\n".join(f"`{r['id']}` **{r['name']}** — {r['origin']} ({r['rarity']})" for r in rows[:40])
        await interaction.response.send_message(
            embed=discord.Embed(title="Seus favoritos", description=texto, color=discord.Color.gold()),
            ephemeral=True,
        )

    @app_commands.command(name="marry", description="Escolhe um personagem da sua coleção como casamento.")
    @app_commands.describe(personagem_id="ID mostrado em /harem")
    async def marry(self, interaction: discord.Interaction, personagem_id: int):
        with conectar() as db:
            owned = db.execute(
                "SELECT id FROM user_characters WHERE character_id = ? AND owner_id = ?",
                (personagem_id, str(interaction.user.id)),
            ).fetchone()
            if not owned:
                await interaction.response.send_message(
                    "Você precisa possuir esse personagem para escolhê-lo.",
                    ephemeral=True,
                )
                return
            db.execute(
                "UPDATE user_characters SET married = 0 WHERE owner_id = ?",
                (str(interaction.user.id),),
            )
            db.execute(
                "UPDATE user_characters SET married = 1 WHERE character_id = ? AND owner_id = ?",
                (personagem_id, str(interaction.user.id)),
            )
            personagem = db.execute(
                "SELECT name FROM characters WHERE id = ?", (personagem_id,)
            ).fetchone()
        await interaction.response.send_message(
            f"♡ {personagem['name']} agora é seu casamento!", ephemeral=False
        )

    @app_commands.command(name="addcharacter", description="Cadastra um personagem (administradores).")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        nome="Nome do personagem",
        origem="Anime, jogo, série ou outra obra",
        raridade="comum, incomum, rara, epica ou lendaria",
        imagem="URL opcional da imagem",
        id_externo="ID opcional único para importar/identificar no JSON",
    )
    @app_commands.choices(raridade=[
        app_commands.Choice(name="Comum", value="comum"),
        app_commands.Choice(name="Incomum", value="incomum"),
        app_commands.Choice(name="Rara", value="rara"),
        app_commands.Choice(name="Épica", value="epica"),
        app_commands.Choice(name="Lendária", value="lendaria"),
    ])
    async def addcharacter(
        self,
        interaction: discord.Interaction,
        nome: str,
        origem: str,
        raridade: app_commands.Choice[str],
        imagem: str = "",
        id_externo: str = "",
    ):
        imagem = imagem.strip()
        if imagem and not imagem.startswith(("https://", "http://")):
            await interaction.response.send_message(
                "A imagem precisa ser um link começando com http:// ou https://.",
                ephemeral=True,
            )
            return
        try:
            with conectar() as db:
                db.execute(
                    """INSERT INTO characters(external_id, name, origin, image_url, rarity)
                       VALUES (?, ?, ?, ?, ?)""",
                    (id_externo.strip() or None, nome.strip(), origem.strip(), imagem, raridade.value),
                )
        except Exception as erro:
            if "UNIQUE constraint failed" in str(erro):
                mensagem = "Esse ID externo já está cadastrado."
            else:
                mensagem = "Não consegui cadastrar. Verifique se os dados estão corretos."
            await interaction.response.send_message(mensagem, ephemeral=True)
            return
        await interaction.response.send_message(
            f"Personagem **{nome}** cadastrado com raridade **{raridade.name}**.",
            ephemeral=True,
        )

    @app_commands.command(name="importcharacters", description="Importa personagens de personagens.json (administradores).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def importcharacters(self, interaction: discord.Interaction):
        caminho = Path(__file__).resolve().parent.parent / "personagens.json"
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except FileNotFoundError:
            await interaction.response.send_message("Não encontrei `personagens.json` na pasta principal.", ephemeral=True)
            return
        except json.JSONDecodeError:
            await interaction.response.send_message("O JSON está inválido. Confira vírgulas, aspas e colchetes.", ephemeral=True)
            return

        if isinstance(dados, dict):
            dados = [dict(valor, id=valor.get("id", chave)) for chave, valor in dados.items()]

        if not isinstance(dados, list):
            await interaction.response.send_message("O JSON precisa conter uma lista de personagens ou um objeto de personagens.", ephemeral=True)
            return

        adicionados = 0
        ignorados = 0
        erros = []
        with conectar() as db:
            for item in dados:
                if not isinstance(item, dict):
                    ignorados += 1
                    continue
                nome = str(item.get("nome", item.get("name", ""))).strip()
                origem = str(item.get("origem", item.get("origin", ""))).strip()
                raridade = str(item.get("raridade", item.get("rarity", "comum"))).strip().lower()
                imagem = str(item.get("imagem", item.get("image_url", ""))).strip()
                external_id = str(item.get("id", "")).strip() or None

                if not nome or not origem or raridade not in RARIDADES:
                    ignorados += 1
                    continue
                if imagem and not imagem.startswith(("https://", "http://")):
                    imagem = ""
                try:
                    db.execute(
                        """INSERT INTO characters(external_id, name, origin, image_url, rarity)
                           VALUES (?, ?, ?, ?, ?)""",
                        (external_id, nome, origem, imagem, raridade),
                    )
                    adicionados += 1
                except Exception:
                    ignorados += 1

        await interaction.response.send_message(
            f"Importação concluída. Adicionados: **{adicionados}**. Ignorados (já existentes ou inválidos): **{ignorados}**.",
            ephemeral=True,
        )

    @app_commands.command(name="personagem", description="Mostra os detalhes de um personagem pelo ID.")
    @app_commands.describe(personagem_id="ID do personagem")
    async def personagem(self, interaction: discord.Interaction, personagem_id: int):
        personagem = buscar_personagem(personagem_id)
        if not personagem:
            await interaction.response.send_message("Não encontrei esse ID.", ephemeral=True)
            return
        with conectar() as db:
            dono = db.execute(
                "SELECT owner_id FROM user_characters WHERE character_id = ?",
                (personagem_id,),
            ).fetchone()
        descricao = f"**Origem:** {personagem['origin']}\n**Raridade:** {personagem['rarity'].title()}\n**ID:** `{personagem['id']}`"
        if dono:
            descricao += f"\n**Dono:** <@{dono['owner_id']}>"
        else:
            descricao += "\n**Dono:** Ninguém — personagem livre"
        await interaction.response.send_message(embed=criar_embed(personagem, descricao))

async def setup(bot):
    await bot.add_cog(Colecao(bot))
