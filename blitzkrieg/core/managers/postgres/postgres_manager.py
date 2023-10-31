from pathlib import Path
from jinja2 import Template
from rich.console import Console
from blitzkrieg.cli.logging_config import setup_logging
from blitzkrieg.cli.step_by_steps import show_generate_compose_file_steps
from blitzkrieg.cli.ui_utils import (
    progress_bar, handle_error, Step, TextComponent, step_by_step, confirm_action
)
from typing import Tuple
from blitzkrieg.core.managers.docker_manager import is_container_ready
from blitzkrieg.core.shared.command_runner import _run_command
from blitzkrieg.core.shared.utils.config import ProjectConfig
from blitzkrieg.core.shared.utils.file_handling import get_template_path
from blitzkrieg.core.shared.utils.networking import find_available_port


backend_logger, ui_logger, console = setup_logging()

def generate_docker_compose_file(project_config: ProjectConfig) -> Path:
    project_name = project_config.project_name
    password = project_config.password


    template_path = get_template_path(project_config.template_dir, 'docker-compose-template.yml')
    if template_path is None:
        handle_error("Template not found", "Please ensure the template exists.")
        return None

    output_path = project_config.instances_dir / f"docker-compose-{project_name}.yml"
    try:
        with open(template_path, 'r') as f:
            template = Template(f.read())

        with open(output_path, 'w') as f:
            rendered = template.render(
                PROJECT_NAME=project_name,
                POSTGRES_USER=project_config.db_user,
                POSTGRES_PASSWORD=password,
                POSTGRES_DB=project_name,
                POSTGRES_PORT=find_available_port(),
                PGADMIN_EMAIL=project_config.admin_email,
                PGADMIN_PASSWORD=password,
                PGADMIN_PORT=find_available_port(5050)
            )
            f.write(rendered)

        console.print("[green]Docker compose file generated successfully![/green]")
        return output_path

    except Exception as e:
        handle_error(f"An unexpected error occurred: {e}", "Check your template and configuration.")
        return None

def start_containers_async(project_config: ProjectConfig) -> Tuple[bool, str]:
    ui_logger.info("start_containers_async called.")
    show_generate_compose_file_steps(project_config.project_name)
    compose_file_path = generate_docker_compose_file(project_config)
    if compose_file_path:
        cmd = f"docker-compose -p {project_config.project_name} -f {compose_file_path} up -d"
        is_ready = is_container_ready(project_config.postgres_container_name)
        if is_ready:
            msg = f"Container {project_config.postgres_container_name} is already running."
            ui_logger.warning(msg)
            return (False, msg)
        else:
            result = _run_command(cmd)  # Actually run the command to start the container
            if result:
                msg = "Containers started successfully."
                print(f"Result: {result}")
                ui_logger.info(msg)
                return (True, msg)
            else:
                msg = "Failed to start containers."
                ui_logger.error(msg)
                return (False, msg)
    else:
        msg = "Failed to generate Docker Compose file."
        ui_logger.error(msg)
        return (False, msg)


def stop_containers_async(project_name: str):
    steps = [
        Step("Stopping Containers", [
            TextComponent("Executing docker-compose down command")
        ])
    ]
    step_by_step(steps)

    cmd = f"docker-compose -f docker-compose-{project_name}.yml down"
    _run_command(cmd)
    ui_logger.info("Containers stopped.")

def initialize_with_persistence_check(project_config: ProjectConfig):
    start_containers_async(project_config)