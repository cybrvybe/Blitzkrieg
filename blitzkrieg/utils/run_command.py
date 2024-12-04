import subprocess
import os
from typing import Union, Tuple, Optional
from blitzkrieg.ui_management.ConsoleInterface import ConsoleInterface
from blitzkrieg.ui_management.console_instance import console

def run_poetry_command(command: list[str], workspace_path: str) -> None:
    try:
        # Prepend 'poetry run' to ensure the command runs inside the Poetry virtual environment
        poetry_command = ['poetry', 'run'] + command

        # Run the command in the workspace directory, ensuring it executes in the Poetry environment
        deactive_venv_result = subprocess.run(['deactivate'], check=False, capture_output=True, text=True)
        result = subprocess.run(poetry_command, cwd=workspace_path, check=True,
                                capture_output=True, text=True)
        reactivate_venv_result = subprocess.run(['source', '.venv/bin/activate'], check=False, capture_output=True, text=True)

        # Handle command output
        console.handle_info(result.stdout)
        if result.stderr:
            console.handle_error(result.stderr)

        if deactive_venv_result.stderr:
            console.handle_error(deactive_venv_result.stderr)

        if reactivate_venv_result.stderr:
            console.handle_error(reactivate_venv_result.stderr)

    except subprocess.CalledProcessError as e:
        # Handle called process errors with detailed information
        console.handle_error(f"Command failed: {e}", e)
        console.handle_error(f"Command stdout:\n{e.stdout}")
        console.handle_error(f"Command stderr:\n{e.stderr}")
        raise

    except Exception as e:
        # Handle any other exceptions
        console.handle_error(f"An error occurred during command execution: {str(e)}", e)
        raise

def run_command(
    command: Union[str, list],
    capture_output: bool = False,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[float] = None,
    encoding: str = 'utf-8'
) -> Tuple[Optional[str], Optional[str], int]:
    """
    Run a shell command and return its output.

    Args:
        command (Union[str, list]): The command to run. Can be a string or a list of arguments.
        capture_output (bool): Whether to capture and return the command's output.
        cwd (Optional[str]): The directory to run the command in. Defaults to the current directory.
        env (Optional[dict]): Environment variables to use for the new process.
        timeout (Optional[float]): The timeout for the command in seconds.
        encoding (str): The encoding to use for decoding the command's output.

    Returns:
        Tuple[Optional[str], Optional[str], int]: A tuple containing (stdout, stderr, return_code).
    """
    try:
        # Display the current working directory
        current_cwd = cwd if cwd else os.getcwd()
        print(f"Running command '{command}' in: {current_cwd}")

        # Prepare the command
        if isinstance(command, str):
            shell = True
        elif isinstance(command, list):
            shell = False
        else:
            raise ValueError("Command must be a string or a list")

        # Run the command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            shell=shell,
            cwd=cwd,
            env=env,
            timeout=timeout,
            encoding=encoding
        )

        # Process the output
        stdout = result.stdout.strip() if capture_output else None
        stderr = result.stderr.strip() if result.stderr else None

        # Print stderr if there's an error
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            if stderr:
                print(f"Error output: {stderr}")

        return stdout, stderr, result.returncode

    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout} seconds")
        return None, "Timeout", -1
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return None, str(e), e.returncode
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, str(e), -1
