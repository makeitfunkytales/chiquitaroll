import discord
from discord import app_commands
from discord.ext import commands

from sistemas.banco import conectar

class Trocas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trocar", description="Propõe uma troca de personagens a outro jogador.")
    @app_commands.describe(
        usuario="Pessoa com quem você quer trocar",
        seu_personagem_id="ID de um personagem seu",
        personagem_desejado_id="ID do personagem que você quer receber",
    )
    async def trocar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        seu_personagem_id: int,
        personagem_desejado_id: int,
    ):
        remetente = str(interaction.user.id)
        destinatario = str(usuario.id)
        if usuario.bot or usuario.id == interaction.user.id:
            await interaction.response.send_message("Escolha outra pessoa que não seja um bot.", ephemeral=True)
            return
        if seu_personagem_id == personagem_desejado_id:
            await interaction.response.send_message("Você não pode oferecer e pedir o mesmo personagem.", ephemeral=True)
            return

        with conectar() as db:
            meu = db.execute(
                "SELECT c.name FROM user_characters uc JOIN characters c ON c.id = uc.character_id WHERE uc.character_id = ? AND uc.owner_id = ?",
                (seu_personagem_id, remetente),
            ).fetchone()
            outro = db.execute(
                "SELECT c.name FROM user_characters uc JOIN characters c ON c.id = uc.character_id WHERE uc.character_id = ? AND uc.owner_id = ?",
                (personagem_desejado_id, destinatario),
            ).fetchone()
            if not meu or not outro:
                await interaction.response.send_message(
                    "A troca não foi criada: confira se você possui o personagem oferecido e se a outra pessoa possui o desejado.",
                    ephemeral=True,
                )
                return
            cursor = db.execute(
                """INSERT INTO trades(from_user, to_user, from_character, to_character)
                   VALUES (?, ?, ?, ?)""",
                (remetente, destinatario, seu_personagem_id, personagem_desejado_id),
            )
            trade_id = cursor.lastrowid

        await interaction.response.send_message(
            f"Proposta de troca **#{trade_id}** enviada para {usuario.mention}.\n"
            f"Você oferece **{meu['name']}** (ID `{seu_personagem_id}`) por **{outro['name']}** (ID `{personagem_desejado_id}`).\n"
            f"{usuario.mention}, use `/aceitartroca troca_id:{trade_id}` ou `/recusartroca troca_id:{trade_id}`.",
        )

    @app_commands.command(name="aceitartroca", description="Aceita uma proposta de troca recebida.")
    async def aceitartroca(self, interaction: discord.Interaction, troca_id: int):
        user_id = str(interaction.user.id)
        with conectar() as db:
            db.execute("BEGIN IMMEDIATE")
            troca = db.execute("SELECT * FROM trades WHERE id = ?", (troca_id,)).fetchone()
            if not troca or troca["status"] != "pending":
                db.rollback()
                await interaction.response.send_message("Essa proposta não existe ou já foi respondida.", ephemeral=True)
                return
            if troca["to_user"] != user_id:
                db.rollback()
                await interaction.response.send_message("Só a pessoa que recebeu a proposta pode aceitá-la.", ephemeral=True)
                return

            dono_a = db.execute(
                "SELECT owner_id FROM user_characters WHERE character_id = ?", (troca["from_character"],)
            ).fetchone()
            dono_b = db.execute(
                "SELECT owner_id FROM user_characters WHERE character_id = ?", (troca["to_character"],)
            ).fetchone()
            if not dono_a or not dono_b or dono_a["owner_id"] != troca["from_user"] or dono_b["owner_id"] != troca["to_user"]:
                db.execute("UPDATE trades SET status = 'invalid' WHERE id = ?", (troca_id,))
                db.commit()
                await interaction.response.send_message("A troca ficou inválida porque a posse de um personagem mudou.", ephemeral=True)
                return

            db.execute(
                "UPDATE user_characters SET owner_id = ?, favorite = 0, married = 0 WHERE character_id = ?",
                (troca["to_user"], troca["from_character"]),
            )
            db.execute(
                "UPDATE user_characters SET owner_id = ?, favorite = 0, married = 0 WHERE character_id = ?",
                (troca["from_user"], troca["to_character"]),
            )
            db.execute("UPDATE trades SET status = 'accepted' WHERE id = ?", (troca_id,))
            db.execute(
                "UPDATE trades SET status = 'cancelled' WHERE status = 'pending' AND id != ? AND (from_character IN (?, ?) OR to_character IN (?, ?))",
                (troca_id, troca["from_character"], troca["to_character"], troca["from_character"], troca["to_character"]),
            )
            db.commit()

        await interaction.response.send_message(f"Troca **#{troca_id}** concluída! Os dois personagens trocaram de dono.")

    @app_commands.command(name="recusartroca", description="Recusa uma proposta de troca recebida.")
    async def recusartroca(self, interaction: discord.Interaction, troca_id: int):
        user_id = str(interaction.user.id)
        with conectar() as db:
            troca = db.execute("SELECT * FROM trades WHERE id = ?", (troca_id,)).fetchone()
            if not troca or troca["status"] != "pending":
                await interaction.response.send_message("Essa proposta não existe ou já foi respondida.", ephemeral=True)
                return
            if troca["to_user"] != user_id:
                await interaction.response.send_message("Só a pessoa que recebeu a proposta pode recusá-la.", ephemeral=True)
                return
            db.execute("UPDATE trades SET status = 'declined' WHERE id = ?", (troca_id,))
        await interaction.response.send_message(f"Proposta **#{troca_id}** recusada.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Trocas(bot))
