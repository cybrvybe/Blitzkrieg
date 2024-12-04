import os
import json
from typing import Optional

import questionary
from blitzkrieg.ui_management.console_instance import console

class BlitzEnvManager:
    def __init__(self):
        self.console = console
        self.file_name = '.blitz.env'
        self.global_env_file_path = os.path.join(os.path.expanduser("~"), ".blitzkrieg", self.file_name)
        self.workspace_name = None
        self.workspace_path = None
        self.workspace_env_file_path = None

    def set_workspace(self, workspace_name: str, workspace_path: Optional[str] = None):
        self.workspace_name = workspace_name
        if workspace_path:
            self.workspace_path = workspace_path
        else:
            self.workspace_path = os.path.join(os.getcwd(), workspace_name)
        self.workspace_env_file_path = os.path.join(self.workspace_path, self.file_name)

    def ensure_global_env_file(self):
        os.makedirs(os.path.dirname(self.global_env_file_path), exist_ok=True)
        if not os.path.exists(self.global_env_file_path):
            with open(self.global_env_file_path, 'w') as f:
                f.write("# Global Blitzkrieg Configuration\n")
        self.console.handle_info(f"Ensured global .blitz.env file at {self.global_env_file_path}")

    def ensure_workspace_env_file(self):
        if not self.workspace_env_file_path:
            self.console.handle_error("Workspace not set. Use set_workspace() first.")
            return
        os.makedirs(os.path.dirname(self.workspace_env_file_path), exist_ok=True)
        if not os.path.exists(self.workspace_env_file_path):
            with open(self.workspace_env_file_path, 'w') as f:
                f.write("# Workspace Blitzkrieg Configuration\n")
                f.write("IS_WORKSPACE=True\n")
        self.console.handle_info(f"Ensured workspace .blitz.env file at {self.workspace_env_file_path}")

    def _get_env_var(self, key: str, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.split('=', 1)[1].strip()
        return None

    def _set_env_var(self, key: str, value: str, file_path: str):
        lines = []
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()

        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break

        if not updated:
            lines.append(f"{key}={value}\n")

        with open(file_path, 'w') as f:
            f.writelines(lines)
            console.handle_info(f"Set {key}={value} in {file_path}")

    def get_global_env_var(self, key: str) -> Optional[str]:
        self.console.handle_info(f"Checking global env var at {self.global_env_file_path} for the key {key}...")
        return self._get_env_var(key, self.global_env_file_path)

    def get_global_env_vars(self) -> dict:
        if not os.path.exists(self.global_env_file_path):
            return {}
        with open(self.global_env_file_path, 'r') as f:
            env_vars = {}
            for line in f:
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip()
            return env_vars

    def set_global_env_var(self, key: str, value: str):
        self._set_env_var(key, value, self.global_env_file_path)

    def delete_global_env_var(self):
        # generate the list of env vars tochoose
        lines = []
        if os.path.exists(self.global_env_file_path):
            with open(self.global_env_file_path, 'r') as f:
                lines = f.readlines()

        updated = False
        choice= questionary.select(
            "Select the environment variable to delete:",
            choices=[line.split('=', 1)[0] for line in lines if '=' in line]
        ).ask()
        lines = [line for line in lines if not line.startswith(f"{choice}=")]

        with open(self.global_env_file_path, 'w') as f:
            f.writelines(lines)
            console.handle_info(f"Deleted {choice} from {self.global_env_file_path}")

    def get_workspace_env_var(self, key: str) -> Optional[str]:
        current_workspace = self.get_global_env_var('CURRENT_WORKSPACE')
        current_workspace_path = self.workspace_env_file_path
        if not self.workspace_env_file_path and not current_workspace:
            self.console.handle_error("Workspace not set. Use set_workspace() first.")
            return None
        if current_workspace:
            current_workspace_path = self.get_global_env_var('CURRENT_WORKSPACE_PATH')
        return self._get_env_var(key, os.path.join(current_workspace_path, self.file_name))

    def set_workspace_env_var(self, key: str, value: str):
        if not self.workspace_env_file_path:
            self.console.handle_error("Workspace not set. Use set_workspace() first.")
            return
        self._set_env_var(key, value, self.workspace_env_file_path)

    def find_workspace_root(self, start_dir: Optional[str] = None) -> Optional[str]:
        current_dir = os.path.abspath(start_dir or os.getcwd())
        while True:
            env_file_path = os.path.join(current_dir, self.file_name)
            if os.path.isfile(env_file_path):
                with open(env_file_path, 'r') as f:
                    if 'IS_WORKSPACE=True' in f.read():
                        return current_dir
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # Reached the root of the file system
                return None
            current_dir = parent_dir

    def is_in_workspace(self) -> bool:
        return self.find_workspace_root() is not None

    def get_current_workspace_name(self) -> Optional[str]:
        workspace_root = self.find_workspace_root()
        if workspace_root:
            return os.path.basename(workspace_root)
        return None

    def get_active_workspace_dir(self):
        console.handle_info(f"About to get current_workspace dir...")
        workspace_name = self.get_global_env_var('CURRENT_WORKSPACE')
        console.handle_info(f"Current workspace name: {workspace_name}")
        if not workspace_name:
            self.console.handle_error("No active workspace found. Use select_workspace() first.")
            return None
        console.handle_info(f"About to get ensure workspace_env_file for {workspace_name}")

        workspace_dir = self.get_global_env_var('CURRENT_WORKSPACE_PATH')
        if not workspace_dir:
            self.console.handle_error("Workspace directory not found. Please ensure the workspace is set up correctly, and that the workspace .blitz.env file has a WORKSPACE_DIRECTORY field.")
            return None
        return workspace_dir
