"""
Discord Mod Accountability Logger
==================================
Logs messages from specified moderator users to a private log channel.

Requirements:
    pip install "discord.py-self>=2.0.1" python-dotenv rich

.env file:
    SPY_TOKEN=your_discord_user_token
    GUILD_ID=550389429567750155
    SOURCE_CHANNEL_ID=550390090665295892
    LOG_CHANNEL_ID=your_private_log_channel_id
    TARGET_USER_IDS=123456789012345678,987654321098765432
"""

from __future__ import annotations

import asyncio
import os
import re
import json
from datetime import datetime, timezone
from typing import Optional, Set

import discord
from discord import Message, Guild, TextChannel, User, Member

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.theme import Theme
from pathlib import Path
import aiohttp
from flask import Flask, jsonify
from threading import Thread
import time

# ── Flask Web Server for Render Uptime ──────────────────────────────────
app = Flask(__name__)

# Global state for uptime monitoring
_bot_state = {
    "status": "starting",
    "started_at": None,
    "messages_logged": 0,
    "edits_logged": 0,
    "deletes_logged": 0,
    "reactions_logged": 0,
    "uptime_seconds": 0,
}

@app.route("/")
def home():
    """Home page with bot status."""
    uptime = "Not started"
    if _bot_state["started_at"]:
        delta = time.time() - _bot_state["started_at"]
        hours = int(delta // 3600)
        minutes = int((delta % 3600) // 60)
        seconds = int(delta % 60)
        uptime = f"{hours}h {minutes}m {seconds}s"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mod Accountability Logger</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: #1a1a2e;
                color: #eee;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background: #16213e;
                border-radius: 16px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                max-width: 420px;
                width: 90%;
                text-align: center;
            }}
            .status {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 20px;
            }}
            .status.online {{ background: #1b5e20; color: #69f0ae; }}
            .status.offline {{ background: #b71c1c; color: #ff8a80; }}
            .status.starting {{ background: #e65100; color: #ffd180; }}
            .dot {{
                width: 10px; height: 10px;
                border-radius: 50%;
                background: currentColor;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.4; }}
            }}
            h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
            .subtitle {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
            .stats {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin-top: 20px;
            }}
            .stat {{
                background: #0f3460;
                padding: 14px;
                border-radius: 10px;
            }}
            .stat-value {{
                font-size: 22px;
                font-weight: 700;
                color: #e94560;
            }}
            .stat-label {{
                font-size: 12px;
                color: #aaa;
                margin-top: 4px;
            }}
            .uptime {{
                margin-top: 20px;
                padding: 12px;
                background: #0f3460;
                border-radius: 10px;
                font-family: monospace;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="status {_bot_state['status']}">
                <span class="dot"></span>
                {_bot_state['status'].upper()}
            </div>
            <h1>🔍 Mod Logger</h1>
            <div class="subtitle">Discord Moderator Accountability</div>

            <div class="uptime">⏱ Uptime: {uptime}</div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{_bot_state['messages_logged']}</div>
                    <div class="stat-label">Messages</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{_bot_state['edits_logged']}</div>
                    <div class="stat-label">Edits</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{_bot_state['deletes_logged']}</div>
                    <div class="stat-label">Deletes</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{_bot_state['reactions_logged']}</div>
                    <div class="stat-label">Reactions</div>
                </div>
            </div>

            <div class="footer">
                Running on Render · discord.py-self
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/health")
def health():
    """Health check endpoint for uptime monitors."""
    return jsonify({
        "status": _bot_state["status"],
        "uptime_seconds": time.time() - _bot_state["started_at"] if _bot_state["started_at"] else 0,
    }), 200 if _bot_state["status"] == "online" else 503

@app.route("/ping")
def ping():
    """Simple ping for uptime bots."""
    return "pong", 200

def run_flask():
    """Run Flask in a background thread."""
    # Render sets PORT env var; default to 10000 for local testing
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ── Start Flask thread before bot ───────────────────────────────────────
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

from flask import Flask, jsonify
from threading import Thread
import time

# ── Flask Web Server for Render Uptime ──────────────────────────────────
app = Flask(__name__)

# Global state for uptime monitoring
_bot_state = {
    "status": "starting",
    "started_at": None,
    "messages_logged": 0,
    "edits_logged": 0,
    "deletes_logged": 0,
    "reactions_logged": 0,
    "uptime_seconds": 0,
}

@app.route("/")
def home():
    """Home page with bot status."""
    uptime = "Not started"
    if _bot_state["started_at"]:
        delta = time.time() - _bot_state["started_at"]
        hours = int(delta // 3600)
        minutes = int((delta % 3600) // 60)
        seconds = int(delta % 60)
        uptime = f"{hours}h {minutes}m {seconds}s"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mod Accountability Logger</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: #1a1a2e;
                color: #eee;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background: #16213e;
                border-radius: 16px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                max-width: 420px;
                width: 90%;
                text-align: center;
            }}
            .status {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 20px;
            }}
            .status.online {{ background: #1b5e20; color: #69f0ae; }}
            .status.offline {{ background: #b71c1c; color: #ff8a80; }}
            .status.starting {{ background: #e65100; color: #ffd180; }}
            .dot {{
                width: 10px; height: 10px;
                border-radius: 50%;
                background: currentColor;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.4; }}
            }}
            h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
            .subtitle {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
            .stats {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin-top: 20px;
            }}
            .stat {{
                background: #0f3460;
                padding: 14px;
                border-radius: 10px;
            }}
            .stat-value {{
                font-size: 22px;
                font-weight: 700;
                color: #e94560;
            }}
            .stat-label {{
                font-size: 12px;
                color: #aaa;
                margin-top: 4px;
            }}
            .uptime {{
                margin-top: 20px;
                padding: 12px;
                background: #0f3460;
                border-radius: 10px;
                font-family: monospace;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="status {_bot_state['status']}">
                <span class="dot"></span>
                {_bot_state['status'].upper()}
            </div>
            <h1>🔍 Mod Logger</h1>
            <div class="subtitle">Discord Moderator Accountability</div>

            <div class="uptime">⏱ Uptime: {uptime}</div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{_bot_state['messages_logged']}</div>
                    <div class="stat-label">Messages</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{_bot_state['edits_logged']}</div>
                    <div class="stat-label">Edits</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{_bot_state['deletes_logged']}</div>
                    <div class="stat-label">Deletes</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{_bot_state['reactions_logged']}</div>
                    <div class="stat-label">Reactions</div>
                </div>
            </div>

            <div class="footer">
                Running on Render · discord.py-self
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/health")
def health():
    """Health check endpoint for uptime monitors."""
    return jsonify({
        "status": _bot_state["status"],
        "uptime_seconds": time.time() - _bot_state["started_at"] if _bot_state["started_at"] else 0,
    }), 200 if _bot_state["status"] == "online" else 503

@app.route("/ping")
def ping():
    """Simple ping for uptime bots."""
    return "pong", 200

def run_flask():
    """Run Flask in a background thread."""
    # Render sets PORT env var; default to 10000 for local testing
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ── Start Flask thread before bot ───────────────────────────────────────
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()


# ── Theme ─────────────────────────────────────────────────────────────────
CUSTOM_THEME = Theme({
    "spy": "bold bright_magenta",
    "mod": "bold bright_cyan",
    "msg": "bright_white",
    "attachment": "bright_yellow",
    "edit": "bright_yellow",
    "delete": "bold bright_red",
    "timestamp": "bright_black",
    "label": "bold bright_cyan",
    "value": "bright_white",
    "separator": "dim",
    "highlight": "bold bright_white",
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "startup": "bold bright_green",
})

console = Console(theme=CUSTOM_THEME, highlight=False)

# ── Config from .env ──────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _env_int(name: str, default: str = "0") -> int:
    raw = os.getenv(name, default)
    raw = raw.strip()
    if raw.startswith("int("):
        raw = raw[4:]
    if raw.endswith(")"):
        raw = raw[:-1]
    raw = raw.strip().strip(chr(34) + chr(39))
    try:
        return int(raw)
    except ValueError:
        console.print(f"[error]ERROR: {name}={raw!r} is not a valid number. Check your .env file.[/error]")
        return 0

TOKEN = os.getenv("SPY_TOKEN", "")
GUILD_ID = _env_int("GUILD_ID")
SOURCE_CHANNEL_ID = _env_int("SOURCE_CHANNEL_ID")
LOG_CHANNEL_ID = _env_int("LOG_CHANNEL_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

_target_ids_str = os.getenv("TARGET_USER_IDS", "")
TARGET_USER_IDS: Set[int] = set()
if _target_ids_str:
    for uid in _target_ids_str.split(","):
        uid = uid.strip()
        if uid:
            try:
                TARGET_USER_IDS.add(int(uid))
            except ValueError:
                pass

# ── Custom Server Emoji Configuration ─────────────────────────────────────
class ServerEmojis:
    """Manages custom server emoji IDs for webhook embeds.

    Uses exact hardcoded emoji IDs with their specific names.
    """

    # Exact emoji IDs as provided
    EMOJI_ID1 = 1528903496433270946      # <:id1:1528903496433270946>
    EMOJI_PIN = 1528904062722900039      # <:pin:1528904062722900039>
    EMOJI_USER = 1528903689849540770     # <:user:1528903689849540770>
    EMOJI_BOT = 1528903852735332373      # <:bot:1528903852735332373>
    EMOJI_LENGTH = 1528903982339068114    # <:length:1528903982339068114>

    def _get(self, emoji_id: int, name: str) -> str:
        if emoji_id and emoji_id > 0:
            return f"<:{name}:{emoji_id}>"
        return ""

    @property
    def id(self) -> str:
        return self._get(self.EMOJI_ID1, "id1") or "🆔"

    @property
    def pin(self) -> str:
        return self._get(self.EMOJI_PIN, "pin") or "📌"

    @property
    def user(self) -> str:
        return self._get(self.EMOJI_USER, "user") or "👤"

    @property
    def clock(self) -> str:
        return "🕐"

    @property
    def channel(self) -> str:
        return "📢"

    @property
    def bot(self) -> str:
        return self._get(self.EMOJI_BOT, "bot") or "🤖"

    @property
    def length(self) -> str:
        return self._get(self.EMOJI_LENGTH, "length") or "📏"

    @property
    def message(self) -> str:
        return self._get(self.EMOJI_ID1, "id1") or "💬"

    @property
    def edit(self) -> str:
        return self._get(self.EMOJI_PIN, "pin") or "✏️"

    @property
    def delete(self) -> str:
        return self._get(self.EMOJI_PIN, "pin") or "🗑️"

    @property
    def reaction(self) -> str:
        return self._get(self.EMOJI_USER, "user") or "😀"

    @property
    def attachment(self) -> str:
        return self._get(self.EMOJI_LENGTH, "length") or "📎"

    @property
    def jump(self) -> str:
        return self._get(self.EMOJI_BOT, "bot") or "🔗"

    @property
    def reply(self) -> str:
        return self._get(self.EMOJI_PIN, "pin") or "↳"

    @property
    def eye(self) -> str:
        return self._get(self.EMOJI_ID1, "id1") or "👁️"

EMOJIS = ServerEmojis()

# ── Rich Logger ───────────────────────────────────────────────────────────
class SpyLogger:
    ICONS = {
        "spy": "[bold bright_magenta]🔍[/bold bright_magenta]",
        "msg": "[bright_white]💬[/bright_white]",
        "edit": "[bright_yellow]✏️[/bright_yellow]",
        "delete": "[bold bright_red]🗑️[/bold bright_red]",
        "attachment": "[bright_yellow]📎[/bright_yellow]",
        "reaction": "[bright_yellow]😀[/bright_yellow]",
        "startup": "[bold bright_green]🚀[/bold bright_green]",
        "info": "[cyan]ℹ️[/cyan]",
        "warning": "[yellow]⚠️[/yellow]",
        "error": "[red]✗[/red]",
    }

    def __init__(self, label: str):
        self.label = label
        self.msg_count = 0
        self.edit_count = 0
        self.delete_count = 0
        self.reaction_count = 0
        self.start_time = datetime.now()

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _print(self, icon_key: str, color: str, text: str):
        ts = f"[bright_black][{self._ts()}][/bright_black]"
        icon = self.ICONS.get(icon_key, "•")
        label = f"[dim][{self.label}][/dim]"
        arrow = f"[{color}]▸[/{color}]"
        console.print(f"{ts} {icon} {label} {arrow} {text}")

    def startup(self, msg: str):
        self._print("startup", "bright_green", f"[bold bright_green]{msg}[/bold bright_green]")

    def info(self, msg: str):
        self._print("info", "cyan", msg)

    def warning(self, msg: str):
        self._print("warning", "yellow", msg)

    def error(self, msg: str):
        self._print("error", "red", msg)

    def msg(self, user: str, content: str, attachments: int = 0):
        self.msg_count += 1
        _bot_state["messages_logged"] = self.msg_count
        att_str = f" [bright_yellow](+{attachments} attachments)[/bright_yellow]" if attachments else ""
        self._print("msg", "bright_white", 
            f"[bold bright_cyan]{user}[/bold bright_cyan]: [bright_white]{content[:200]}[/bright_white]{att_str}"
        )

    def edit(self, user: str, before: str, after: str):
        self.edit_count += 1
        _bot_state["edits_logged"] = self.edit_count
        self._print("edit", "bright_yellow",
            f"[bold bright_cyan]{user}[/bold bright_cyan] [dim]edited:[/dim]\n"
            f"  [bright_red]-[/bright_red] {before[:100]}\n"
            f"  [bright_green]+[/bright_green] {after[:100]}"
        )

    def delete(self, user: str, content: str):
        self.delete_count += 1
        _bot_state["deletes_logged"] = self.delete_count
        self._print("delete", "bright_red",
            f"[bold bright_cyan]{user}[/bold bright_cyan] [bold bright_red]DELETED:[/bold bright_red] [dim]{content[:200]}[/dim]"
        )

    def attachment(self, user: str, url: str, filename: str):
        self._print("attachment", "bright_yellow",
            f"[bold bright_cyan]{user}[/bold bright_cyan] [bright_yellow]📎 {filename}[/bright_yellow]"
        )

    def banner(self):
        banner = """
[bold bright_magenta]╔══════════════════════════════════════════════════════════════════╗[/bold bright_magenta]
[bold bright_cyan]║[/bold bright_cyan]  [bold bright_magenta]🔍[/bold bright_magenta]   [bold bright_white]MOD[/bold bright_white] [bold bright_cyan]ACCOUNTABILITY[/bold bright_cyan] [bold bright_white]LOGGER[/bold bright_white]   [bold bright_magenta]📋[/bold bright_magenta]                        [bold bright_cyan]║[/bold bright_cyan]
[bold bright_blue]╠══════════════════════════════════════════════════════════════════╣[/bold bright_blue]
[bold bright_green]║[/bold bright_green]  [dim]Purpose:[/dim] [bold bright_white]Monitor moderator messages for transparency[/bold bright_white]     [bold bright_green]║[/bold bright_green]
[bold bright_yellow]║[/bold bright_yellow]  [dim]Features:[/dim] [bold bright_cyan]Message[/bold bright_cyan] [dim]|[/dim] [bold bright_yellow]Edit[/bold bright_yellow] [dim]|[/dim] [bold bright_red]Delete[/bold bright_red] [dim]|[/dim] [bold bright_green]Attachment[/bold bright_green] [dim]logging[/dim]        [bold bright_yellow]║[/bold bright_yellow]
[bold bright_magenta]╚══════════════════════════════════════════════════════════════════╝[/bold bright_magenta]
"""
        console.print(banner)

    def status_panel(self):
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        table = Table(box=box.ROUNDED, border_style="bright_magenta", show_header=False)
        table.add_column("Metric", style="bold bright_cyan")
        table.add_column("Value", style="bright_white")
        table.add_row("⏱ Uptime", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        table.add_row("💬 Messages", f"[bright_white]{self.msg_count}[/bright_white]")
        table.add_row("✏️ Edits", f"[bright_yellow]{self.edit_count}[/bright_yellow]")
        table.add_row("🗑️ Deletes", f"[bright_red]{self.delete_count}[/bright_red]")
        table.add_row("🎯 Targets", f"[bold bright_cyan]{len(TARGET_USER_IDS)}[/bold bright_cyan] users")

        panel = Panel(
            table,
            title="[bold bright_magenta]📊 Logger Status[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.ROUNDED,
        )
        console.print(panel)


# ── File Logger ───────────────────────────────────────────────────────────
class FileLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.log_dir / f"mod_log_{self.date_str}.txt"
        self._write("=" * 70)
        self._write(f"MOD ACCOUNTABILITY LOG — Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._write(f"Guild: {GUILD_ID} | Source: {SOURCE_CHANNEL_ID} | Targets: {len(TARGET_USER_IDS)} users")
        self._write("=" * 70)
        self._write("")

    def _write(self, text: str):
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self.date_str:
            self.date_str = current_date
            self.log_file = self.log_dir / f"mod_log_{self.date_str}.txt"
            self._write("=" * 70)
            self._write(f"NEW DAY — {self.date_str}")
            self._write("=" * 70)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_message(self, user: str, user_id: int, content: str, channel: str, msg_id: int, attachments: int = 0):
        att_str = f" [+{attachments} attachments]" if attachments else ""
        self._write(f"[{self._timestamp()}] [MESSAGE] {user} [ID:{user_id}] in #{channel}: {content}{att_str} (MSG_ID: {msg_id})")

    def log_edit(self, user: str, user_id: int, before: str, after: str, channel: str, msg_id: int):
        self._write(f"[{self._timestamp()}] [EDIT] {user} [ID:{user_id}] in #{channel} (MSG_ID: {msg_id})")
        self._write(f"  BEFORE: {before}")
        self._write(f"  AFTER:  {after}")

    def log_delete(self, user: str, user_id: int, content: str, channel: str, msg_id: int):
        self._write(f"[{self._timestamp()}] [DELETE] {user} [ID:{user_id}] in #{channel}: {content} (MSG_ID: {msg_id})")

    def log_reaction(self, user: str, user_id: int, emoji: str, channel: str, msg_preview: str):
        self._write(f"[{self._timestamp()}] [REACTION] {user} [ID:{user_id}] reacted {emoji} in #{channel} to: {msg_preview}")

    def log_info(self, text: str):
        self._write(f"[{self._timestamp()}] [INFO] {text}")

    def log_warning(self, text: str):
        self._write(f"[{self._timestamp()}] [WARN] {text}")

    def log_error(self, text: str):
        self._write(f"[{self._timestamp()}] [ERROR] {text}")


# ── Color Constants ──────────────────────────────────────────────────────
class EmbedColors:
    LIGHT_PINK = 0xFFB6C1

# ── Main Client ───────────────────────────────────────────────────────────
class ModLogger(discord.Client):
    def __init__(self):
        super().__init__(chunk_guilds_at_startup=False)
        self.log = SpyLogger("MOD-LOG")
        self.file_log = FileLogger(log_dir="logs")
        self.source_channel: Optional[TextChannel] = None
        self.log_channel: Optional[TextChannel] = None
        self.guild: Optional[Guild] = None
        self._cached_users: dict[int, str] = {}

    async def _user_name(self, user_id: int) -> str:
        if user_id in self._cached_users:
            return self._cached_users[user_id]
        if self.guild:
            member = self.guild.get_member(user_id)
            if member:
                name = f"{member.display_name} ({member.name})"
                self._cached_users[user_id] = name
                return name
        try:
            if self.guild:
                member = await self.guild.fetch_member(user_id)
                if member:
                    name = f"{member.display_name} ({member.name})"
                    self._cached_users[user_id] = name
                    return name
        except Exception:
            pass
        try:
            user = await self.fetch_user(user_id)
            if user:
                name = f"{user.display_name} ({user.name})"
                self._cached_users[user_id] = name
                return name
        except discord.NotFound:
            pass
        except Exception:
            pass
        return f"User-{user_id}"

    def _is_target(self, user_id: int) -> bool:
        return user_id in TARGET_USER_IDS

    def _build_line_embed(self, title: str, description_lines: list[str], color: int, author: discord.User | discord.Member, timestamp: datetime, footer_text: str = "") -> discord.Embed:
        description = "\n".join(description_lines)
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=timestamp,
        )
        avatar_url = author.display_avatar.url if author.display_avatar else None
        embed.set_author(
            name=f"{author.display_name} (@{author.name})",
            icon_url=avatar_url,
            url=f"https://discord.com/users/{author.id}"
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        footer = footer_text if footer_text else f"User ID: {author.id} • Mod Accountability Logger"
        embed.set_footer(
            text=footer,
            icon_url="https://cdn.discordapp.com/emojis/1042824983613456424.webp"
        )
        return embed

    def _format_reply_context(self, message: Message) -> str | None:
        if not message.reference or not message.reference.message_id:
            return None
        ref = message.reference
        reply_to_author = ref.resolved.author if ref.resolved else None
        if reply_to_author:
            return f"{EMOJIS.reply} **Replying to:** {reply_to_author.mention} (`@{reply_to_author.name}`)"
        return f"{EMOJIS.reply} **Replying to:** message `{ref.message_id}`"

    async def _send_log(self, embed: discord.Embed, ping_text: str | None = None):
        """Send log via webhook with optional notification text."""
        if WEBHOOK_URL:
            try:
                await self._send_webhook(embed, ping_text)
                return
            except Exception as e:
                self.log.error(f"Webhook failed: {e}")
                self.file_log.log_error(f"Webhook failed: {e}")
        if self.log_channel:
            try:
                plain_text = self._embed_to_text(embed)
                if len(plain_text) > 1900:
                    plain_text = plain_text[:1900] + "\n... (truncated)"
                await self.log_channel.send(plain_text)
            except Exception as e2:
                self.log.error(f"Failed to send log: {e2}")
                self.file_log.log_error(f"Failed to send Discord log: {e2}")

    async def _send_webhook(self, embed: discord.Embed, ping_text: str | None = None):
        """Send embed via Discord webhook with content text."""
        embed_dict = embed.to_dict()

        if "timestamp" in embed_dict and embed_dict["timestamp"] is not None:
            if hasattr(embed_dict["timestamp"], "isoformat"):
                embed_dict["timestamp"] = embed_dict["timestamp"].isoformat()

        keys_to_remove = []
        for key, value in embed_dict.items():
            if value is None or value == {} or value == []:
                if key not in ("title", "description", "color"):
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            del embed_dict[key]

        if "color" in embed_dict and embed_dict["color"] is not None:
            embed_dict["color"] = int(embed_dict["color"])

        if not embed_dict.get("title") and not embed_dict.get("description"):
            raise ValueError("Embed must have at least a title or description")

        payload = {
            "username": "Mod-Log",
            "avatar_url": "https://cdn.discordapp.com/emojis/1042824983613456424.webp",
            "embeds": [embed_dict],
        }

        if ping_text:
            payload["content"] = ping_text

        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload) as resp:
                response_text = await resp.text()
                if resp.status not in (200, 204):
                    raise Exception(f"Webhook returned {resp.status}: {response_text}")
                self.log.info(f"Webhook sent successfully (status {resp.status})")

    def _embed_to_text(self, embed: discord.Embed) -> str:
        lines = []
        if embed.title:
            title = re.sub(r'<a?:\w+:\d+>', '', embed.title).strip()
            lines.append(f"**{title}**")
        if embed.description:
            desc = re.sub(r'<a?:\w+:\d+>', '', embed.description)
            lines.append(desc)
        for field in embed.fields:
            name = re.sub(r'<a?:\w+:\d+>', '', field.name).strip()
            value = re.sub(r'<a?:\w+:\d+>', '', field.value)
            lines.append(f"**{name}**: {value}")
        if embed.footer:
            lines.append(f"_{embed.footer.text}_")
        if embed.timestamp:
            lines.append(f"`{embed.timestamp}`")
        return "\n".join(lines)

    async def on_ready(self):
        _bot_state["status"] = "online"
        _bot_state["started_at"] = time.time()
        self.log.banner()
        self.log.startup(f"Logged in as [bold bright_white]{self.user}[/bold bright_white] (ID: {self.user.id})")
        self.file_log.log_info(f"Bot started as {self.user} (ID: {self.user.id})")

        self.guild = self.get_guild(GUILD_ID)
        if not self.guild:
            try:
                self.guild = await self.fetch_guild(GUILD_ID)
            except Exception as e:
                self.log.error(f"Cannot access guild {GUILD_ID}: {e}")
                self.file_log.log_error(f"Cannot access guild {GUILD_ID}: {e}")
                await self.close()
                return

        self.source_channel = self.get_channel(SOURCE_CHANNEL_ID)
        self.log_channel = self.get_channel(LOG_CHANNEL_ID)
        if not self.source_channel:
            try:
                self.source_channel = await self.fetch_channel(SOURCE_CHANNEL_ID)
            except Exception as e:
                self.log.warning(f"Source channel fetch failed: {e}")
                self.file_log.log_warning(f"Source channel fetch failed: {e}")
        if not self.log_channel:
            try:
                self.log_channel = await self.fetch_channel(LOG_CHANNEL_ID)
            except Exception as e:
                self.log.warning(f"Log channel fetch failed: {e}")
                self.file_log.log_warning(f"Log channel fetch failed: {e}")

        if not TARGET_USER_IDS:
            self.log.warning("No target users configured! Set TARGET_USER_IDS in .env")
            self.file_log.log_warning("No target users configured")
        else:
            targets_str = ", ".join(str(uid) for uid in TARGET_USER_IDS)
            self.log.info(f"Monitoring [bold bright_cyan]{len(TARGET_USER_IDS)}[/bold bright_cyan] users: {targets_str}")
            self.file_log.log_info(f"Monitoring {len(TARGET_USER_IDS)} users: {targets_str}")
        self.log.status_panel()

    async def on_message(self, message: Message):
        if not self._is_target(message.author.id):
            return
        if message.guild and message.guild.id != GUILD_ID:
            return
        user_name = await self._user_name(message.author.id)
        content = message.content or "[empty message]"
        has_attachments = len(message.attachments)
        channel_name = getattr(message.channel, 'name', str(message.channel.id))
        self.log.msg(user_name, content, has_attachments)
        self.file_log.log_message(user_name, message.author.id, content, channel_name, message.id, has_attachments)

        lines = []
        lines.append(f"{EMOJIS.user} **User:** {message.author.mention} (`@{message.author.name}`)")
        lines.append(f"{EMOJIS.channel} **Channel:** <#{message.channel.id}> (`#{channel_name}`)")
        lines.append(f"{EMOJIS.clock} **Sent:** <t:{int(message.created_at.timestamp())}:F>")
        lines.append("")

        reply_context = self._format_reply_context(message)
        if reply_context:
            lines.append(reply_context)
            lines.append("")

        lines.append(f"{EMOJIS.message} **Content:**")
        lines.append(f"```{content[:3900] or '[empty message]'}```")

        if has_attachments:
            lines.append("")
            lines.append(f"{EMOJIS.attachment} **Attachments ({has_attachments}):**")
            for att in message.attachments[:5]:
                lines.append(f"• [{att.filename}]({att.url})")
            if has_attachments > 5:
                lines.append(f"• *...and {has_attachments - 5} more*")

        lines.append("")
        lines.append(f"{EMOJIS.id} **Message ID:** `{message.id}`")
        lines.append(f"{EMOJIS.length} **Length:** `{len(content)}` characters")
        lines.append(f"{EMOJIS.bot} **Bot:** {'Yes' if message.author.bot else 'No'}")
        if message.jump_url:
            lines.append(f"{EMOJIS.jump} **Jump:** [Click Here]({message.jump_url})")

        embed = self._build_line_embed(
            title=f"{EMOJIS.message} New Message",
            description_lines=lines,
            color=EmbedColors.LIGHT_PINK,
            author=message.author,
            timestamp=message.created_at,
            footer_text=f"Message ID: {message.id} • #{channel_name}"
        )

        safe_ping = f"{EMOJIS.eye} **@{message.author.name}** sent a message"
        await self._send_log(embed, ping_text=safe_ping)

    async def on_message_edit(self, before: Message, after: Message):
        if not self._is_target(after.author.id):
            return
        if after.guild and after.guild.id != GUILD_ID:
            return
        if before.content == after.content:
            return
        user_name = await self._user_name(after.author.id)
        before_content = before.content or "[empty]"
        after_content = after.content or "[empty]"
        channel_name = getattr(after.channel, 'name', str(after.channel.id))
        self.log.edit(user_name, before_content, after_content)
        self.file_log.log_edit(user_name, after.author.id, before_content, after_content, channel_name, after.id)

        lines = []
        lines.append(f"{EMOJIS.user} **User:** {after.author.mention} (`@{after.author.name}`)")
        lines.append(f"{EMOJIS.channel} **Channel:** <#{after.channel.id}> (`#{channel_name}`)")
        if after.edited_at:
            lines.append(f"{EMOJIS.clock} **Edited:** <t:{int(after.edited_at.timestamp())}:F>")
        else:
            lines.append(f"{EMOJIS.clock} **Edited:** Just now")
        lines.append("")

        lines.append(f"{EMOJIS.message} **Before:**")
        lines.append(f"```{before_content[:1000] or '[empty]'}```")
        lines.append("")

        lines.append(f"{EMOJIS.edit} **After:**")
        lines.append(f"```{after_content[:1000] or '[empty]'}```")
        lines.append("")

        lines.append(f"{EMOJIS.pin} **Changes:**")
        lines.append(f"• Length: `{len(before_content)}` → `{len(after_content)}` chars")
        if before_content != after_content:
            before_words = set(before_content.split())
            after_words = set(after_content.split())
            added = after_words - before_words
            removed = before_words - after_words
            if added:
                lines.append(f"• Added: {', '.join(f'`{w}`' for w in list(added)[:5])}")
            if removed:
                lines.append(f"• Removed: {', '.join(f'`{w}`' for w in list(removed)[:5])}")

        lines.append("")
        lines.append(f"{EMOJIS.id} **Message ID:** `{after.id}`")
        if after.jump_url:
            lines.append(f"{EMOJIS.jump} **Jump:** [Click Here]({after.jump_url})")

        embed = self._build_line_embed(
            title=f"{EMOJIS.edit} Message Edited",
            description_lines=lines,
            color=EmbedColors.LIGHT_PINK,
            author=after.author,
            timestamp=after.edited_at or datetime.now(timezone.utc),
            footer_text=f"Message ID: {after.id} • #{channel_name}"
        )

        safe_ping = f"{EMOJIS.eye} **@{after.author.name}** edited a message"
        await self._send_log(embed, ping_text=safe_ping)

    async def on_message_delete(self, message: Message):
        if not message.author:
            return
        if not self._is_target(message.author.id):
            return
        if message.guild and message.guild.id != GUILD_ID:
            return
        user_name = await self._user_name(message.author.id)
        content = message.content or "[empty or embed]"
        channel_name = getattr(message.channel, 'name', str(message.channel.id))
        self.log.delete(user_name, content)
        self.file_log.log_delete(user_name, message.author.id, content, channel_name, message.id)

        lines = []
        lines.append(f"{EMOJIS.user} **User:** {message.author.mention} (`@{message.author.name}`)")
        lines.append(f"{EMOJIS.channel} **Channel:** <#{message.channel.id}> (`#{channel_name}`)")
        lines.append(f"{EMOJIS.clock} **Deleted:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>")
        lines.append("")

        lines.append(f"{EMOJIS.delete} **Deleted Content:**")
        lines.append(f"```{content[:1000] or '[empty or embed]'}```")
        lines.append("")

        if message.created_at:
            try:
                deletion_time = datetime.now(message.created_at.tzinfo) if message.created_at.tzinfo else datetime.now(timezone.utc)
                age = deletion_time - message.created_at
                hours, remainder = divmod(int(age.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                lines.append(f"{EMOJIS.clock} **Message Age:** `{hours}h {minutes}m {seconds}s` old when deleted")
                lines.append(f"{EMOJIS.clock} **Originally Sent:** <t:{int(message.created_at.timestamp())}:F>")
                lines.append("")
            except Exception:
                lines.append(f"{EMOJIS.clock} **Originally Sent:** <t:{int(message.created_at.timestamp())}:F>")
                lines.append("")

        lines.append(f"{EMOJIS.id} **Message ID:** `{message.id}`")

        embed = self._build_line_embed(
            title=f"{EMOJIS.delete} Message Deleted",
            description_lines=lines,
            color=EmbedColors.LIGHT_PINK,
            author=message.author,
            timestamp=datetime.now(timezone.utc),
            footer_text=f"Message ID: {message.id} • #{channel_name}"
        )

        safe_ping = f"{EMOJIS.eye} **@{message.author.name}** deleted a message"
        await self._send_log(embed, ping_text=safe_ping)

    async def on_reaction_add(self, reaction, user):
        if not self._is_target(user.id):
            return
        user_name = await self._user_name(user.id)
        emoji = str(reaction.emoji)
        msg_content = reaction.message.content or "[embed/file]"
        channel_name = getattr(reaction.message.channel, 'name', str(reaction.message.channel.id))
        self.log._print("reaction", "bright_yellow",
            f"[bold bright_cyan]{user_name}[/bold bright_cyan] reacted [bold bright_yellow]{emoji}[/bold bright_yellow] to: [dim]{msg_content[:80]}[/dim]"
        )
        self.log.reaction_count += 1
        _bot_state["reactions_logged"] = self.log.reaction_count
        self.log.reaction_count += 1
        _bot_state["reactions_logged"] = self.log.reaction_count
        self.file_log.log_reaction(user_name, user.id, emoji, channel_name, msg_content[:200])

        lines = []
        lines.append(f"{EMOJIS.user} **User:** {user.mention} (`@{user.name}`)")
        lines.append(f"{EMOJIS.reaction} **Emoji:** {emoji}")
        lines.append(f"{EMOJIS.channel} **Channel:** <#{reaction.message.channel.id}> (`#{channel_name}`)")
        lines.append(f"{EMOJIS.clock} **Reacted:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>")
        lines.append("")

        msg_author = reaction.message.author
        if msg_author:
            lines.append(f"{EMOJIS.user} **Message Author:** {msg_author.mention} (`@{msg_author.name}`)")
        else:
            lines.append(f"{EMOJIS.user} **Message Author:** Unknown")
        lines.append(f"{EMOJIS.message} **Message Content:**")
        lines.append(f"```{msg_content[:500] or '[embed/file]'}```")
        lines.append("")

        try:
            if getattr(reaction.message, 'jump_url', None):
                lines.append(f"{EMOJIS.jump} **Jump:** [Click Here]({reaction.message.jump_url})")
        except Exception:
            pass
        lines.append(f"{EMOJIS.id} **Message ID:** `{reaction.message.id}`")

        embed = self._build_line_embed(
            title=f"{EMOJIS.reaction} Reaction Added",
            description_lines=lines,
            color=EmbedColors.LIGHT_PINK,
            author=user,
            timestamp=datetime.now(timezone.utc),
            footer_text=f"Message ID: {reaction.message.id} • #{channel_name}"
        )

        safe_ping = f"{EMOJIS.eye} **@{user.name}** reacted to a message"
        await self._send_log(embed, ping_text=safe_ping)


# ── Entrypoint ────────────────────────────────────────────────────────────
def _warn_snowflake(name: str, value: int):
    digits = len(str(value))
    if not (17 <= digits <= 19):
        console.print(f"[warning]WARNING: {name} = {value} has {digits} digits. Expected 17-19.[/warning]")

async def main():
    _bot_state["status"] = "starting"
    if not TOKEN:
        console.print("[error]ERROR: Set SPY_TOKEN in .env[/error]")
        return
    if GUILD_ID == 0:
        console.print("[error]ERROR: Set GUILD_ID in .env[/error]")
        return
    if SOURCE_CHANNEL_ID == 0:
        console.print("[error]ERROR: Set SOURCE_CHANNEL_ID in .env[/error]")
        return
    if not WEBHOOK_URL and LOG_CHANNEL_ID == 0:
        console.print("[warning]WARNING: Neither WEBHOOK_URL nor LOG_CHANNEL_ID set. Logs will only appear in console and file.[/warning]")
    elif WEBHOOK_URL:
        console.print("[success]Webhook logging enabled[/success]")
    if not TARGET_USER_IDS:
        console.print("[warning]WARNING: TARGET_USER_IDS not set. No users will be monitored.[/warning]")
    _warn_snowflake("GUILD_ID", GUILD_ID)
    _warn_snowflake("SOURCE_CHANNEL_ID", SOURCE_CHANNEL_ID)
    if LOG_CHANNEL_ID:
        _warn_snowflake("LOG_CHANNEL_ID", LOG_CHANNEL_ID)
    client = ModLogger()
    try:
        await client.start(TOKEN)
    except discord.LoginFailure as e:
        console.print(f"[error]Invalid token: {e}[/error]")
    except Exception as e:
        console.print(f"[error]Failed to start: {e!r}[/error]")
    finally:
        _bot_state["status"] = "offline"
        if not client.is_closed():
            await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped by user.[/dim]")
