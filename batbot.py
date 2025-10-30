from discord.ext import commands
import discord
import asyncio
import logging
import json
import datetime
import os
from discord import app_commands

# ========================
# CONFIGURAÇÕES E LOG
# ========================

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents)

# IDs e constantes
GUILD_ID = 908146730812444702
WELCOME_CHANNEL_ID = 1430978650374930544

cargo_streamer = 1069555253063729183
cargo_sigma = 1067183251757727744
cargo_capa = 909196062156259368
cargo_lambda = 1069553734620807199

CARGOS_POR_TEMPO = {
    7 * 3600: cargo_lambda,       # 7h
    24 * 3600: cargo_sigma,       # 24h
    168 * 3600: cargo_sigma,      # 7 dias
}

DATA_FILE = "voice_times.json"

# ========================
# DADOS LOCAIS
# ========================

try:
    with open(DATA_FILE, "r") as f:
        voice_times = json.load(f)
except FileNotFoundError:
    voice_times = {}

join_times = {}

# ========================
# VIEW: BOTÕES DE CARGO
# ========================

class EscolhaCargo(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Streamer 🟣",
        style=discord.ButtonStyle.danger,
        custom_id="streamer_role"
    )
    async def streamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(cargo_streamer)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Cargo **{role.name}** removido!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Cargo **{role.name}** adicionado!", ephemeral=True)

# ========================
# EVENTOS
# ========================

@bot.event
async def on_member_join(member):
    guild = member.guild
    channel = guild.get_channel(WELCOME_CHANNEL_ID)

    embed = discord.Embed(
        title="👋 Bem-vindo!",
        description="Escolha seu cargo abaixo:",
        color=discord.Color.red()
    )

    thread = await channel.create_thread(
        name=f"boas-vindas-{member.name}",
        type=discord.ChannelType.private_thread,
        invitable=False
    )

    await thread.add_user(member)
    await thread.send(embed=embed, view=EscolhaCargo())

    await asyncio.sleep(120)
    await thread.delete()

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="O Pai Tá ON!")
    )

    bot.add_view(EscolhaCargo())

    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Sincronizados {len(synced)} comandos locais com o servidor {GUILD_ID}.")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")

    print(f"🤖 Bot online como {bot.user}")

# ========================
# SISTEMA DE HORAS EM VOZ
# ========================

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = str(member.id)

    # Entrou em canal de voz
    if before.channel is None and after.channel is not None:
        join_times[user_id] = datetime.datetime.utcnow()

    # Saiu do canal de voz
    elif before.channel is not None and after.channel is None:
        if user_id in join_times:
            delta = datetime.datetime.utcnow() - join_times[user_id]
            segundos = delta.total_seconds()
            total = voice_times.get(user_id, 0) + segundos
            voice_times[user_id] = total
            del join_times[user_id]

            await checar_cargos(member, total)

            with open(DATA_FILE, "w") as f:
                json.dump(voice_times, f)

# ========================
# FUNÇÃO DE CHECAGEM
# ========================

async def checar_cargos(member, total):
    for tempo, cargo_id in sorted(CARGOS_POR_TEMPO.items()):
        cargo = member.guild.get_role(cargo_id)
        if total >= tempo and cargo not in member.roles:
            await member.add_roles(cargo)
            print(f"{member.name} recebeu o cargo {cargo.name} (após {tempo} segundos).")
            try:
                await member.send(f"🎉 Você conquistou o cargo **{cargo.name}** por atingir {tempo/3600:.2f} horas em chamadas de voz!")
            except discord.Forbidden:
                pass

# ========================
# COMANDOS LOCAIS (slash)
# ========================

@bot.tree.command(
    name="ping",
    description="Responde com Pong!",
    guild=discord.Object(id=GUILD_ID)
)
async def ping(interaction: discord.Interaction):
    # Responde instantaneamente sem mensagem de carregamento
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)


@bot.tree.command(
    name="limpar_chat",
    description="Apaga todas as mensagens deste canal (somente administradores).",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.checks.has_permissions(administrator=True)
async def limpar_chat(interaction: discord.Interaction):
    # Mostra mensagem personalizada imediata
    await interaction.response.send_message("🦇 Limpando a Bat-Caverna...", ephemeral=True)

    canal = interaction.channel
    try:
        # Apaga até 1000 mensagens
        apagadas = await canal.purge(limit=1000)

        # Mensagem de confirmação
        await interaction.followup.send(
            f"✅ Canal limpo! ({len(apagadas)} mensagens apagadas)",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Sem permissão para apagar mensagens.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erro ao limpar o chat: `{e}`", ephemeral=True)


# ========================
# EXECUÇÃO
# ========================

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
