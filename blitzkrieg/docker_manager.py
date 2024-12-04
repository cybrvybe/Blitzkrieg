# docker_manager.py

import docker
from docker.errors import NotFound, APIError
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.ui_management.ConsoleInterface import ConsoleInterface
from blitzkrieg.ui_management.console_instance import console
import time



class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.console: ConsoleInterface = console
        self.blitz_env_manager = blitz_env_manager

    def create_docker_network(self, network_name):
        """Create a Docker network if it doesn't exist."""
        try:
            self.console.handle_wait(f"Creating docker network {network_name} to run workspace containers together")
            network = self.client.networks.create(network_name)
            self.blitz_env_manager.set_workspace_env_var('NETWORK_NAME', network_name)
            self.console.handle_success(f"Network '{network_name}' created successfully.")


            return network

        except Exception as e:
            return self.console.handle_error(f"Failed to create network: {str(e)}")

    def run_container(self, container_name, image_name, network_name, env_vars, ports, volumes, detach=True):
        """Run a Docker container."""
        try:
            self.client.containers.run(
                image_name,
                name=container_name,
                network=network_name,
                environment=env_vars,
                ports=ports,
                volumes=volumes,
                detach=detach
            )
            self.wait_for_container(container_name)

        except APIError as e:
            return self.console.handle_error(f"Failed to run container: {str(e)}")
        except Exception as e:
            return self.console.handle_error(f"Failed to run container: {str(e)}")


    def wait_for_container(self, container_name, timeout=10000, interval=1):
        """Wait for container to be in running state."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            self.console.handle_wait(f"Waiting for container {container_name} to start...")
            time.sleep(10)
            try:
                container = self.client.containers.get(container_name)
                if container.status == 'running':
                    container_attrs = container.attrs
                    success_message = f"Container [white]{container_name}[/white] is running"
                    self.console.handle_success(success_message)
                    return container_attrs
                self.console.handle_info(f"Container {container_name} is not running yet. Waiting...")
                time.sleep(interval)
            except NotFound:
                self.console.handle_error(f"Container {container_name} not found.")
                return None
            except APIError as e:
                self.console.handle_error(f"Failed to get container status: {str(e)}")
                return None
            except Exception as e:
                message = f"Failed to wait for container '{container_name}': {str(e)}"
                self.console.handle_error(message)
                return None
        self.console.handle_error(f"Timeout exceeded while waiting for container {container_name} to start.")
        return None

    def remove_container(self, app, container_name):
        """Remove a Docker container."""
        try:
            app.handle_info(f"Removing container {container_name}...")
            container = self.client.containers.get(container_name)
            container.remove(force=True)
            app.handle_success(f"Container [white]'{container_name}'[/white] removed successfully.")
        except NotFound as e:
            app.handle_error(f"Container {container_name} not found.")
        except APIError as e:
            app.handle_error(f"Failed to remove container [white]{container_name}[/white]: {str(e)}")
        except Exception as e:
            app.handle_error(f"Failed to remove container [white]{container_name}[/white]: {str(e)}")

    def remove_volume(self, app, volume_name):
        """Remove a Docker volume."""
        try:
            app.handle_info(f"Removing volume {volume_name}...")
            volume = self.client.volumes.get(volume_name)
            volume.remove()
            return True
        except NotFound as e:
            app.handle_error(f"Volume {volume_name} not found.")
            return False

    def remove_all_volumes(self, app):
        """Remove all Docker volumes."""
        try:
            for volume in self.client.volumes.list():
                volume.remove()
            volume_names = [v.name for v in self.client.volumes.list()]
            csv_volume_names = ', '.join(volume_names)
            app.handle_success(f"The following volumes have been removed successfully: {csv_volume_names}")
        except NotFound as e:
            app.handle_error(f"Volume not found.")
        except APIError as e:
            app.handle_error(f"Failed to remove volume: {str(e)}")
        except Exception as e:
            app.handle_error(f"Failed to remove volume: {str(e)}")

    def remove_docker_network(self, app, network_name):
        """Remove a Docker network."""
        try:
            network = self.client.networks.get(network_name)
            network.remove()
            app.handle_success(f"Network [white]{network_name}[/white] removed successfully.")
        except NotFound as e:
            app.handle_error(f"Network {network_name} not found.")
        except APIError as e:
            app.handle_error(f"Failed to remove network [white]{network_name}[/white] due to APIError: {str(e)}")
        except Exception as e:
            app.handle_error(f"Failed to remove network [white]{network_name}[/white]: {str(e)}")
