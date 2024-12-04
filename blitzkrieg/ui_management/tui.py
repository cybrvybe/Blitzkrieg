from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Button, Static
from textual.binding import Binding
from textual.reactive import reactive
from textual import on
from rich.syntax import Syntax
from rich.text import Text
from textual.screen import Screen
from textual.css.query import NoMatches
from textual.command import Command, CommandPalette, Provider, Hit, Hits
import pyperclip
import inspect
import click
import asyncio

from blitzkrieg.workspace_manager import WorkspaceManager
class ClickCommandProvider(Provider):
    def __init__(self, screen: Screen, match_style: any):
        super().__init__(screen, match_style)
        self._app = None
        self._commands = {}

    @property
    def app(self):
        if self._app is None:
            self._app = self.screen.app
        return self._app

    @property
    def commands(self):
        if not self._commands:
            self._commands = getattr(self.app, 'commands', {})
        return self._commands

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for cmd_name, cmd in self.commands.items():
            score = matcher.match(cmd_name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(cmd_name),
                    lambda cmd=cmd: self.app.execute_command(cmd),
                    help=getattr(cmd, 'help', None) or getattr(cmd, 'short_help', None)
                )

    async def delete_workspace(self) -> any:
        from blitzkrieg.workspace_manager import WorkspaceManager
        WorkspaceManager().teardown_workspace(self.app)

class TextualApp(App):
    CSS = """
    #sidebar {
        width: 30%;
        background: $panel;
        border-right: solid $primary;
    }

    #main-content {
        width: 70%;
    }

    RichLog {
        height: 1fr;
        border: solid $accent;
        padding: 1 2;
        overflow-y: auto;
    }

    #input {
        dock: bottom;
    }

    Button {
        width: 100%;
    }

    .command-button {
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("y", "copy_output", "Copy Output"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
        Binding("ctrl+p", "command_palette", "Command Palette"),
    ]

    COMMANDS = App.COMMANDS | {ClickCommandProvider}


    def __init__(self, commands):
        super().__init__()
        self.commands = {cmd.name: cmd for cmd in commands}
        self.log_storage = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                RichLog(id="output"),
                id="main-content"
            )
        )
        yield Input(id="input", placeholder="Enter command arguments...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(RichLog).focus()

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        self.selected_command = self.commands[event.button.label]
        self.handle_info(f"Selected command: {event.button.label}")

    async def run_command(self, command_name: str) -> None:
        command = self.commands[command_name]
        await self.execute_command(command)

    async def execute_command(self, command, **kwargs):
        self.display_phase("Running Command")
        self.handle_info(f"Running command: {command.name}")

        try:
            ctx = click.Context(command, info_name=command.name, parent=None, obj=self)
            with ctx:
                result = await self.run_sync(command.callback, **kwargs)
            self.handle_success(f"Command executed successfully: {result}")
        except click.exceptions.ClickException as e:
            self.handle_error(f"Command execution failed: {str(e)}")
        except Exception as e:
            self.handle_error(f"An unexpected error occurred: {str(e)}")

    async def run_sync(self, func, **kwargs):
        return await self.loop.run_in_executor(None, func, **kwargs)

    def action_clear_log(self):
        """Clear the log output."""
        self.query_one(RichLog).clear()
        self.log_storage.clear()
        self.handle_info("Log cleared.")

    def append_log(self, log_message: str, style: str = ""):
        output = self.query_one(RichLog)
        if isinstance(log_message, str):
            rich_text = Text(log_message, style=style)
            self.log_storage.append(rich_text.plain)
            output.write(rich_text)
        else:
            output.write(log_message)
            self.log_storage.append(str(log_message))

    def handle_info(self, message):
        self.append_log(message, style="cyan")

    def handle_error(self, message):
        self.append_log(message, style="bold red")

    def handle_success(self, message):
        self.append_log(message, style="bold green")

    def display_phase(self, phase_name):
        self.append_log(f"== {phase_name.upper()} ==", style="bold yellow")

    def display_file_content(self, file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
            syntax = Syntax(content, "python", theme="monokai", line_numbers=True)
            self.append_log(syntax)
        except Exception as e:
            self.handle_error(f"Failed to load file {file_path}: {str(e)}")

    def action_copy_output(self):
        """Copy the log output to clipboard."""
        log_content = "\n".join(self.log_storage)
        try:
            pyperclip.copy(log_content)
            self.handle_success("Output successfully copied to clipboard.")
        except Exception as e:
            self.handle_error(f"Failed to copy to clipboard: {str(e)}")

    def action_command_palette(self) -> None:
        """Open the command palette."""
        self.push_screen(CommandPalette())

def run_tui(commands=None):
    if not commands:
        print("No commands provided to run_tui function.")
        return
    print(f"Initializing TextualApp with {len(commands)} commands.")
    app = TextualApp(commands)
    app.run()
