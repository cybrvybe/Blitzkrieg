import time

from cli.ui import print_warning
from core.shared.command_runner import CommandRunner

class ContainerManager:
    def __init__(self, container_name):
        self.container_name = container_name
        self.runner = CommandRunner()

    def start_container(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def container_exists(self):
        existing_containers = self.runner.run_command(f"docker ps -a -q -f name={self.container_name}")
        return bool(existing_containers)

    def remove_container(self):
        if self.container_exists():
            print_warning(f"Container with name {self.container_name} already exists. Stopping and removing...")
            self.runner.run_command(f"docker stop {self.container_name}")
            self.runner.run_command(f"docker rm {self.container_name}")
            time.sleep(5)  # Give Docker a few seconds to free up the name

    def is_container_running(self):
        output = self.runner.run_command(f"docker inspect -f '{{{{.State.Running}}}}' {self.container_name}")
        return output == 'true'