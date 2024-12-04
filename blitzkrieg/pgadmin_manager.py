# pgadmin_manager.py

import json
import os
import tarfile
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.utils.port_allocation import find_available_port
from blitzkrieg.ui_management.ConsoleInterface import ConsoleInterface

class PgAdminManager:
    def __init__(
            self,
            postgres_port,
            pgadmin_port=None,
            workspace_name: str = None,
            console: ConsoleInterface = None,
    ):
        self.blitz_env_manager = blitz_env_manager
        self.workspace_name = workspace_name
        self.network_name = f"{self.workspace_name}-network"
        self.container_name = f"{self.workspace_name}-pgadmin"
        self.pgadmin_port = pgadmin_port if pgadmin_port else find_available_port()
        self.pgadmin_port_2 = find_available_port(443)
        self.postgres_port = postgres_port
        self.console_interface = console if console else ConsoleInterface()
        self.postgres_server_config_name = f"{self.workspace_name.capitalize()} PostgreSQL"
        self.postgres_server_config_host = f"{self.workspace_name}-postgres"
        self.postgres_server_config_username = f"{self.workspace_name}-db-user"
        self.pgadmin_binding_config_path = '/pgadmin4/servers.json'
        self.console = console
        self.servers_config_path = os.path.join(os.getcwd(), self.workspace_name, 'servers.json')

    def teardown(self):
        self.docker_manager.remove_container(self.container_name)
        self.docker_manager.remove_all_volumes()

    def setup_pgadmin(self):
        self.create_server_config()
        self.start_pgadmin_container()

    def create_server_config(self):
        self.console.handle_wait("Creating server configuration for PgAdmin...")
        servers_config = {
            "Servers": {
                "1": {
                    "Name": self.postgres_server_config_name,
                    "Group": "Servers",
                    "Host": self.postgres_server_config_host,
                    "Port": self.postgres_port,
                    "MaintenanceDB": self.workspace_name,
                    "Username": self.postgres_server_config_username,
                    "SSLMode": "prefer"
                }
            }
        }
        servers_config_path = os.path.join(os.getcwd(), self.workspace_name, 'servers.json')
        with open(servers_config_path, 'w') as f:
            self.console.handle_wait(f"Writing server configuration to {servers_config_path}...")
            json.dump(servers_config, f)
        self.console.handle_info(f"Server configuration written to {servers_config_path}")

    def start_pgadmin_container(self):
        self.console.handle_wait("Starting PgAdmin container...")
        servers_config_path = os.path.join(os.getcwd(), 'servers.json')
        volume_bind = {servers_config_path: {'bind': self.pgadmin_binding_config_path, 'mode': 'ro'}}

        self.docker_manager.run_container(
            self.container_name,
            "dpage/pgadmin4",
            self.network_name,
            {
                "PGADMIN_DEFAULT_EMAIL": self.blitz_env_manager.get_global_env_var('EMAIL'),
                "PGADMIN_DEFAULT_PASSWORD": self.blitz_env_manager.get_global_env_var('PASSWORD')
            },
            {'80/tcp': self.pgadmin_port},
            volume_bind
        )
        self.console_interface.handle_info(f"PgAdmin Successfully Initialized at [white]http://localhost:{self.pgadmin_port}[/white] with servers.json bind mounted.")
