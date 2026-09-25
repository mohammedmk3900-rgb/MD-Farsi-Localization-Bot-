from __future__ import annotations

import json

import discord
from discord import app_commands

from app.application import application
from app.services.commands import CommandService
from app.services.permissions import allowed

commands = CommandService()
intents = discord.Intents.none()
intents.guilds = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def render(data: object) -> str:
    return "json\n" + json.dumps(data, ensure_ascii=False, indent=2)[:1900]


def member_role(interaction: discord.Interaction) -> str:
    if not isinstance(interaction.user, discord.Member):
        return "contributor"
    names = {role.name.casefold() for role in interaction.user.roles}
    mapping = (
        ("owner", {"owner", "مالک"}),
        ("project_manager", {"project manager", "مدیر پروژه"}),
        ("review_manager", {"review manager", "مدیر بازبینی"}),
        ("reviewer", {"reviewer", "بازبین"}),
        ("translator", {"translator", "مترجم"}),
        ("contributor", {"contributor", "مشارکت‌کننده"}),
    )
    for role, aliases in mapping:
        if names & aliases:
            return role
    return "contributor"


def require(interaction: discord.Interaction, permission: str) -> bool:
    role = member_role(interaction)
    return allowed(role, permission)


async def deny(interaction: discord.Interaction) -> None:
    message = "⛔ دسترسی لازم برای این عملیات را نداری."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.event
async def on_ready():
    application.record("discord.ready", {
        "guild_id": application.context.settings.discord_guild_id,
        "connected": True,
    })
    await tree.sync()


project = app_commands.Group(name="project", description="MD Farsi Localization project")


@project.command(name="status", description="نمایش وضعیت سامانه")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.status()), ephemeral=True)


@project.command(name="stats", description="نمایش آخرین آمار ذخیره‌شده")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.stats()), ephemeral=True)


@project.command(name="progress", description="نمایش آخرین پیشرفت ذخیره‌شده")
async def progress(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.progress()), ephemeral=True)


@project.command(name="center", description="مرکز فرمان V10")
async def center(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.command_center()), ephemeral=True)


@project.command(name="glossary", description="واژه‌نامه زنده ParaTranz")
async def glossary(interaction: discord.Interaction, page: int = 1):
    if not require(interaction, "glossary.read"):
        await deny(interaction)
        return
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(render(commands.glossary(page)), ephemeral=True)


@project.command(name="history", description="تاریخچه Snapshotها")
async def history(interaction: discord.Interaction, limit: int = 10):
    await interaction.response.send_message(render(commands.history(limit)), ephemeral=True)


@project.command(name="health", description="سلامت سامانه")
async def health(interaction: discord.Interaction):
    if not require(interaction, "health.read"):
        await deny(interaction)
        return
    await interaction.response.send_message(render(commands.health()), ephemeral=True)


@project.command(name="achievements", description="نقاط عطف پروژه")
async def achievements(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.achievements()), ephemeral=True)


@project.command(name="sync", description="همگام‌سازی مستقیم با ParaTranz")
async def sync(interaction: discord.Interaction):
    if not require(interaction, "sync.run"):
        await deny(interaction)
        return
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(render(commands.sync()), ephemeral=True)


@project.command(name="report", description="گزارش پروژه")
@app_commands.describe(period="daily یا weekly")
async def report(interaction: discord.Interaction, period: str = "daily"):
    if not require(interaction, "report.read"):
        await deny(interaction)
        return
    if period not in {"daily", "weekly"}:
        await interaction.response.send_message("period باید daily یا weekly باشد.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(render(commands.report(period)), ephemeral=True)


@project.command(name="tasks", description="صف مأموریت‌های مترجمان")
async def tasks(interaction: discord.Interaction, status: str = "all"):
    if not require(interaction, "tasks.self"):
        await deny(interaction)
        return
    await interaction.response.send_message(
        render({"summary": commands.task_summary(), "items": commands.tasks(None if status == "all" else status)}),
        ephemeral=True,
    )


@project.command(name="task_create", description="ساخت مأموریت ترجمه")
async def task_create(interaction: discord.Interaction, title: str, scope: str = "", priority: str = "normal"):
    if not require(interaction, "tasks.manage"):
        await deny(interaction)
        return
    try:
        result = commands.create_task(title, scope, priority)
    except ValueError as error:
        await interaction.response.send_message(f"خطا: {error}", ephemeral=True)
        return
    await interaction.response.send_message(render(result), ephemeral=True)


@project.command(name="task_claim", description="گرفتن یک مأموریت")
async def task_claim(interaction: discord.Interaction, task_id: int):
    if not require(interaction, "tasks.self"):
        await deny(interaction)
        return
    try:
        result = commands.claim_task(task_id, str(interaction.user.id))
    except (KeyError, ValueError) as error:
        await interaction.response.send_message(f"خطا: {error}", ephemeral=True)
        return
    await interaction.response.send_message(render(result), ephemeral=True)


@project.command(name="task_submit", description="ارسال مأموریت برای بازبینی")
async def task_submit(interaction: discord.Interaction, task_id: int):
    if not require(interaction, "tasks.self"):
        await deny(interaction)
        return
    try:
        result = commands.submit_task(task_id, str(interaction.user.id))
    except (KeyError, ValueError) as error:
        await interaction.response.send_message(f"خطا: {error}", ephemeral=True)
        return
    await interaction.response.send_message(render(result), ephemeral=True)


@project.command(name="task_complete", description="تأیید مأموریت پس از بازبینی")
async def task_complete(interaction: discord.Interaction, task_id: int):
    if not require(interaction, "tasks.review"):
        await deny(interaction)
        return
    try:
        result = commands.complete_task(task_id, str(interaction.user.id))
    except (KeyError, ValueError) as error:
        await interaction.response.send_message(f"خطا: {error}", ephemeral=True)
        return
    await interaction.response.send_message(render(result), ephemeral=True)


@project.command(name="check", description="بررسی ترجمه بدون انتشار خودکار")
async def check(interaction: discord.Interaction, source: str, translation: str):
    if not require(interaction, "translation.check"):
        await deny(interaction)
        return
    await interaction.response.defer(ephemeral=True)
    result = commands.check_translation(source, translation)
    await interaction.followup.send(render(result), ephemeral=True)


@project.command(name="help", description="فهرست فرمان‌های پروژه")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("\n".join(commands.help()), ephemeral=True)


tree.add_command(project)


def run() -> None:
    token = application.context.settings.discord_bot_token
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    bot.run(token)
