import itertools
import json
import subprocess
import sys
import threading
import time
import logging
from typing import Any, Dict, List, Callable
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from rich.traceback import Traceback
from rich import box
from rich.syntax import Syntax
from termcolor import colored
import shutil
import pyperclip
import io
import os
import random

# Setup structured and colored logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(level=logging.INFO)]
)

class Logger:
    def __init__(self):
        self.console = Console()
        self.output_buffer = io.StringIO()

    def log(self, message):
        logging.info(message)
        self.output_buffer.write(f"{message}\n")

    def log_json(self, title: str, data: Any, style: str = "bold green"):
        json_str = json.dumps(data, indent=4, sort_keys=True)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        panel = Panel(syntax, title=title, border_style=style, expand=True)
        self.console.print(panel)
        self.output_buffer.write(f"{title}: {json_str}\n")

    def log_error(self, message: str, data: Any = None):
        if data:
            json_str = json.dumps(data, indent=4, sort_keys=True)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            panel = Panel(syntax, title=message, border_style="red", expand=True)
        else:
            panel = Panel(message, title="Error", border_style="red", expand=True)
        self.console.print(panel)
        self.output_buffer.write(f"Error: {message}\n{json_str if data else ''}\n")

    def get_output(self):
        return self.output_buffer.getvalue()

class CustomSpinner:
    def __init__(self, text='Loading...', spinner_chars=None, interval=0.1):
        self._text = text
        self.spinner_chars = spinner_chars if spinner_chars else [
            "⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓",
            "⠙⠚⠞⠖⠦⠴⠲⠳⠓⠋",
            "⠚⠞⠖⠦⠴⠲⠳⠓⠋⠙",
            "⠞⠖⠦⠴⠲⠳⠓⠋⠙⠚",
            "⠖⠦⠴⠲⠳⠓⠋⠙⠚⠞",
            "⠦⠴⠲⠳⠓⠋⠙⠚⠞⠖",
            "⠴⠲⠳⠓⠋⠙⠚⠞⠖⠦",
            "⠲⠳⠓⠋⠙⠚⠞⠖⠦⠴",
            "⠳⠓⠋⠙⠚⠞⠖⠦⠴⠲",
            "⠓⠋⠙⠚⠞⠖⠦⠴⠲⠳",
        ]
        self.interval = interval
        self.stop_running = threading.Event()
        self.thread = threading.Thread(target=self._spin)
        self.lock = threading.Lock()

    def start(self):
        if not self.thread.is_alive():
            self.stop_running.clear()
            self.thread = threading.Thread(target=self._spin)
            self.thread.start()

    def stop(self):
        self.stop_running.set()
        self.thread.join()
        self._clear_line()

    def succeed(self, message):
        self.stop()
        self._animate_message(message, "✔", "green")

    def fail(self, message):
        self.stop()
        self._animate_message(message, "✖", "red")

    def info(self, message):
        self.stop()
        self._animate_message(message, "ℹ", "blue")

    def _spin(self):
        frame_iter = itertools.cycle(self.spinner_chars)
        while not self.stop_running.is_set():
            with self.lock:
                sys.stdout.write(f"\r{colored(next(frame_iter), 'blue')} {self._text}")
                sys.stdout.flush()
            time.sleep(self.interval)

    def _clear_line(self):
        columns = shutil.get_terminal_size().columns
        sys.stdout.write('\r' + ' ' * columns + '\r')
        sys.stdout.flush()

    def _animate_message(self, message, symbol, color):
        self._clear_line()
        sys.stdout.write(colored(f"{symbol} {message}\n", color))
        sys.stdout.flush()

class FileManager:
    def __init__(self):
        self.console = Console()
        self.output_buffer = io.StringIO()

    def display_file_content(self, file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        file_extension = file_path.split('.')[-1]
        lexer = {
            'py': 'python',
            'json': 'json',
            'md': 'markdown',
            'sh': 'bash',
            'html': 'html',
            'css': 'css',
            'js': 'javascript'
        }.get(file_extension, 'text')
        syntax = Syntax(content, lexer, theme='monokai', line_numbers=True)
        self.console.print(syntax)
        self.output_buffer.write(content + "\n")

    def file_exists(self, file_path):
        return os.path.isfile(file_path)


class CommandExecutor:
    def __init__(self, logger: Logger, spinner: CustomSpinner):
        self.logger = logger
        self.spinner = spinner

    def execute_command(self, command, directory, message=None):
        self.spinner.stop()
        self.spinner.text = (message if message else f"Executing command: {' '.join(command)}")
        self.spinner.start()
        if command[0] == 'pip':
            full_command = [sys.executable, '-m'] + command
        else:
            full_command = command
        try:
            result = subprocess.run(
                full_command, cwd=directory, shell=False, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            command_output = {
                "args": result.args,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            self.spinner.stop()
            self.logger.log_json("Command Output", self._parse_output(command_output), style="green")
            return result
        except subprocess.CalledProcessError as e:
            error_details = {
                "returncode": e.returncode,
                "cmd": e.cmd,
                "output": e.output,
                "stderr": e.stderr
            }
            self.logger.log_error(f"Command {command} failed with error", self._parse_output(error_details))
            self.spinner.stop()
            return None
        except Exception as e:
            self.logger.log_error("Unexpected Error", str(e))
            self.spinner.stop()
            return None

    def execute_docker_command(self, command, directory, message=None):
        self.spinner.stop()
        self.spinner.text = (message if message else f"Executing Docker command: {' '.join(command)}")
        self.spinner.start()
        try:
            result = subprocess.run(
                command, cwd=directory, shell=False, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            command_output = {
                "args": result.args,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            self.spinner.stop()
            self.logger.log_json("Docker Command Output", self._parse_docker_output(command_output), style="green")
            return result
        except subprocess.CalledProcessError as e:
            error_details = {
                "returncode": e.returncode,
                "cmd": e.cmd,
                "output": e.output,
                "stderr": e.stderr
            }
            self.logger.log_error(f"Docker command {command} failed with error", self._parse_docker_output(error_details))
            self.spinner.stop()
            return None
        except Exception as e:
            self.logger.log_error("Unexpected Error", str(e))
            self.spinner.stop()
            return None

    def _parse_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        parsed_output = {}
        if 'stdout' in output and output['stdout']:
            parsed_output['stdout'] = self._parse_lines(output['stdout'])
        if 'stderr' in output and output['stderr']:
            parsed_output['stderr'] = self._parse_lines(output['stderr'])
        return parsed_output

    def _parse_lines(self, text: str) -> List[str]:
        lines = text.strip().split('\n')
        filtered_lines = [line for line in lines if line.strip()]
        return filtered_lines

    def _parse_docker_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        parsed_output = {}
        if 'stdout' in output and output['stdout']:
            parsed_output['stdout'] = self._filter_docker_lines(output['stdout'])
        if 'stderr' in output and output['stderr']:
            parsed_output['stderr'] = self._filter_docker_lines(output['stderr'])
        return parsed_output

    def _filter_docker_lines(self, text: str) -> List[str]:
        essential_keywords = ['done', 'Creating', 'Created', 'Starting', 'Started', 'exporting', 'successfully']
        lines = text.strip().split('\n')
        filtered_lines = [line for line in lines if any(keyword in line for keyword in essential_keywords)]
        return filtered_lines

class ClipboardManager:
    def __init__(self, logger: Logger):
        self.logger = logger

    def copy_to_clipboard(self, text):
        pyperclip.copy(text)
        self.logger.log("Output copied to clipboard.")

class DisplayManager:
    def __init__(self):
        self.console = Console()
        self.output_buffer = io.StringIO()

    def display_banner(self, text):
        banner_panel = Panel(Text(text, style="bold magenta"), border_style="magenta", expand=False, box=box.ROUNDED)
        self.console.print("\n")
        self.console.print(banner_panel)
        self.output_buffer.write(f"### {text} ###\n")

    def display_subphase(self, text):
        self.console.print(Text(text, style="bold blue"))
        self.output_buffer.write(f"--- {text} ---\n")

    def display_action_status(self, action_name, status, symbol, color):
        status_panel = Panel(Text(f"{symbol} {action_name} - {status}", style=f"bold {color}"), border_style=color, box=box.SQUARE)
        self.console.print(status_panel)
        self.output_buffer.write(f"{symbol} {action_name} - {status}\n")

class Action:
    def __init__(self, name: str, func: Callable, **kwargs):
        self.name = name
        self.func = func
        self.args = kwargs
        self.status = 'pending'

    def run(self):
        self.func(**self.args)
        self.status = 'completed'

class Phase:
    def __init__(self, title: str):
        self.title = title
        self.actions: List[Action] = []
        self.status = 'pending'

    def add_action(self, name: str, func: Callable, **kwargs):
        action = Action(name, func, **kwargs)
        self.actions.append(action)
        return action

    def run(self):
        for action in self.actions:
            action.run()
        self.status = 'completed'
class ConsoleInterface:
    def __init__(self):
        self.logger = Logger()
        self.file_manager = FileManager()
        self.spinner = CustomSpinner(text='Initializing...', interval=0.1)
        self.command_executor = CommandExecutor(self.logger, spinner=self.spinner)
        self.clipboard_manager = ClipboardManager(self.logger)
        self.display_manager = DisplayManager()
        self.workflows: List[Dict[str, Any]] = []
        self.current_phase = None

    def create_workflow(self, workflow_name: str) -> Dict[str, Any]:
        workflow = {'name': workflow_name, 'phases': []}
        self.workflows.append(workflow)
        return workflow

    def create_phase(self, workflow: Dict[str, Any], title: str) -> Phase:
        phase = Phase(title)
        workflow['phases'].append(phase)
        return phase

    def add_action(self, phase: Phase, name: str, func: Callable, **kwargs) -> Action:
        action = phase.add_action(name, func, **kwargs)
        return action

    def handle_success(self, message):
        self._ensure_spinner_started()
        self.spinner.succeed(message)
        self.logger.output_buffer.write(f"✔ {message}\n")
        self.spinner.stop()

    def handle_error(self, message, error_object=None):
        self._ensure_spinner_started()
        self.spinner.fail(message)
        self.logger.output_buffer.write(f"✖ {message}\n")

        if error_object:
            error_details = {}
            for key, value in error_object.__dict__.items():
                if key == 'stderr':
                    # Format the traceback
                    try:
                        tb = Traceback.from_exception(type(error_object), error_object, error_object.__traceback__)
                        error_details[key] = tb
                    except:
                        error_details[key] = value  # Fallback to original stderr if formatting fails
                else:
                    error_details[key] = value

            error_panel = Panel(
                Syntax(json.dumps(error_details, default=str, sort_keys=True, indent=4), "json", theme="monokai", line_numbers=True),
                title="Error Details",
                title_align="left",
                border_style="red",
                expand=False,
                box=box.DOUBLE,
            )
            self.logger.console.print(error_panel)

            # Print formatted traceback separately for better readability
            if 'stderr' in error_details and isinstance(error_details['stderr'], Traceback):
                self.logger.console.print("\nDetailed Traceback:")
                self.logger.console.print(error_details['stderr'])
        else:
            self.logger.console.print(Panel(f"[bold red]{message}", border_style="red"))

        self.spinner.stop()
    def handle_wait(self, message):
        self._ensure_spinner_started()
        self.spinner.text = message
        self.spinner.start()
        self.logger.output_buffer.write(f"... {message}\n")
        self.spinner.stop()

    def display_llm_system_chat_response_display(self, response):
        # randomize the color of the response
        color = ['red', 'green', 'yellow', 'blue', 'magenta',
                    'cyan', 'white', 'bright_red', 'bright_green',
                    'bright_yellow', 'bright_blue', 'bright_magenta',
                    'bright_cyan', 'bright_white']
        color = color[random.randint(0, len(color) - 1)]

        # format the text to be displayed in monospace
        response = f"```\n{response}\
                    \n```"



        # create cool chat display box for llm responses
        box = Panel(
            Text(response, style=f"bold {color}"),
            title="LLM Response",
            title_align="left",
            border_style="green",
            expand=False
        )
        self.logger.console.print(box)

    def handle_info(self, message):
        self._ensure_spinner_started()
        self.spinner.info(message)
        self.logger.output_buffer.write(f"ℹ {message}\n")
        self.spinner.stop()

    def run_workflow(self, workflow: Dict[str, Any]):
        for phase in workflow['phases']:
            self.current_phase = phase
            self.display_manager.display_banner(phase.title)
            for action in phase.actions:
                self.run_action(action)
            phase.status = 'completed'
        self.clipboard_manager.copy_to_clipboard(self.logger.get_output())

    def run_action(self, action: Action):
        self.spinner.text = action.name
        self.spinner.start()
        try:
            action.run()
            self.handle_success(f"Completed {action.name}")
        except Exception as e:
            self.handle_error(f"An error has occurred while {action.name}: {str(e)}")
        finally:
            self.spinner.stop()

    def execute_command(self, command, directory, message=None):
        try:
            self._ensure_spinner_started()
            result = self.command_executor.execute_command(command, directory, message)
            self.spinner.stop()
            return result
        except Exception as e:
            self.spinner.stop()
            self.handle_error(f"Command {' '.join(command)} failed: {str(e)}")

    def execute_docker_command(self, command, directory, message=None):
        try:
            self._ensure_spinner_started()
            result = self.command_executor.execute_docker_command(command, directory, message)
            self.spinner.stop()
            return result
        except Exception as e:
            self.spinner.stop()
            self.handle_error(f"Docker command {' '.join(command)} failed: {str(e)}")

    def display_file_content(self, file_path):
        self.file_manager.display_file_content(file_path)

    def _ensure_spinner_started(self):
        if not self.spinner.thread.is_alive():
            self.spinner.start()
