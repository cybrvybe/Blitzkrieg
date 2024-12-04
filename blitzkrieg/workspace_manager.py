# main_blitzkrieg.py

from prettytable import PrettyTable
import questionary
from blitzkrieg.alembic_manager import AlembicManager
from blitzkrieg.class_instances.cookie_cutter_manager import cookie_cutter_manager
from blitzkrieg.class_instances.docker_manager import docker_manager
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.file_manager import FileManager
from blitzkrieg.workspace_directory_manager import WorkspaceDirectoryManager
from blitzkrieg.pgadmin_manager import PgAdminManager
from blitzkrieg.postgres_manager import WorkspaceDbManager
from blitzkrieg.utils.port_allocation import find_available_port
from blitzkrieg.ui_management.ConsoleInterface import ConsoleInterface
from blitzkrieg.ui_management.console_instance import console
import os
from prettytable import PrettyTable

from blitzkrieg.workspace_management.templates.managers.workspace_docker_manager import WorkspaceDockerManager

class WorkspaceManager:
    def __init__(self, workspace_name=None):

        self.blitz_env_manager = blitz_env_manager
        self.workspace_name = workspace_name
        self.console: ConsoleInterface = console
        self.docker_manager = docker_manager
        self.postgres_port: int = find_available_port(5432)
        self.pgadmin_port: int = find_available_port(5050)
        self.pgadmin_manager:PgAdminManager = PgAdminManager(
            postgres_port=self.postgres_port,
            pgadmin_port=self.pgadmin_port,
            workspace_name=self.workspace_name,
            console=self.console
        )
        self.file_manager: FileManager = FileManager()
        self.workspace_db_manager: WorkspaceDbManager = WorkspaceDbManager(
            port=self.postgres_port,
            workspace_name=self.workspace_name
        )
        self.workspace_directory_manager: WorkspaceDirectoryManager = WorkspaceDirectoryManager(
            workspace_name=self.workspace_name,
            console_interface=self.console
        )
        self.workspace_db_manager.set_workspace_directory_manager(self.workspace_directory_manager)
        self.docker_network_name: str = f"{self.workspace_name}-network"
        self.cwd = os.getcwd()
        self.alembic_manager: AlembicManager = AlembicManager(
            db_manager=self.workspace_db_manager,
            workspace_name=self.workspace_name,
            file_manager=self.file_manager,
            console=self.console
        )
        self.workspace_db_manager.set_alembic_manager(self.alembic_manager)
        self.workspace_db_manager.set_pgadmin_manager(self.pgadmin_manager)
        self.file_manager = FileManager()
        self.workspace_docker_manager = WorkspaceDockerManager()


    def blitz_init(self):
        blitzkrieg_initialization_process = self.console.create_workflow("Blitzkrieg Initialization")

        workspace_directory_initalization_group = self.console.create_phase(blitzkrieg_initialization_process, "Workspace Directory Initialization")
        workspace_env_file_initialization = self.console.create_phase(blitzkrieg_initialization_process, "Workspace Environment File Initialization")
        workspace_container_initialization = self.console.create_phase(blitzkrieg_initialization_process, "Workspace Container Initialization")
        database_initialization = self.console.create_phase(blitzkrieg_initialization_process, "Database Initialization")

        self.console.add_action(
            phase=workspace_env_file_initialization,
            name="Creating workspace .blitz.env file",
            func=self.blitz_env_manager.ensure_workspace_env_file
        )

        self.console.add_action(
            phase=workspace_env_file_initialization,
            name="Creating global .blitz.env file",
            func=self.blitz_env_manager.ensure_global_env_file
        )

        self.console.add_action(
            phase=workspace_env_file_initialization,
            name="Storing workspace configuration in .env file...",
            func=self.store_credentials,postgres_port=self.postgres_port
        )

        # Directory initialization
        self.console.add_action(
            phase=workspace_directory_initalization_group,
            name="Creating workspace directory...",
            func=cookie_cutter_manager.generate_workspace,
            workspace_name=self.workspace_name,
            postgres_port=self.postgres_port
        )

        self.console.add_action(
            phase=workspace_directory_initalization_group,
            name="Setting up poetry environment for project",
            func=self.workspace_directory_manager.setup_poetry_environment
        )

        self.console.add_action(
            phase=workspace_directory_initalization_group,
            name="Creating workspace docker network",
            func=self.docker_manager.create_docker_network,
            network_name=self.docker_network_name
        )

        self.console.add_action(
            phase=workspace_directory_initalization_group,
            func=self.alembic_manager.create_sqlalchemy_models_directory,
            name="Creating /sqlalchemy_models directory"
        )

        self.console.add_action(
            phase=workspace_directory_initalization_group,
            func=self.alembic_manager.copy_sqlalchemy_models,
            name="Copying SQLAlchemy Models",
            migration_epoch_key='initial_migration_epoch'
        )

        self.console.add_action(
            phase=workspace_env_file_initialization,
            name="Saving workspace directory details to workspace .blitz.env",
            func=self.workspace_directory_manager.save_workspace_directory_details_to_env_file
        )

        # Container initialization
        self.console.add_action(
            phase=workspace_container_initialization,
            name="Building workspace container...",
            func=self.workspace_docker_manager.build_workspace_container
        )

        self.console.add_action(
            phase=workspace_container_initialization,
            name="Starting workspace container...",
            func=self.workspace_docker_manager.start_workspace_container
        )

        # Database initialization
        self.console.add_action(
            phase=database_initialization,
            name="Waiting for database to be ready...",
            func=self.alembic_manager.wait_for_db
        )

        self.console.add_action(
            phase=database_initialization,
            name="Creating project_management schema...",
            func=self.alembic_manager.create_schema
        )

        self.console.add_action(
            phase=database_initialization,
            name="Initializing Alembic...",
            func=self.alembic_manager.initialize_alembic
        )

        self.console.add_action(
            phase=database_initialization,
            name="Copying over readme.py model",
            func=self.alembic_manager.copy_sqlalchemy_models,
            migration_epoch_key='readme_migration_epoch'
        )

        self.console.add_action(
            phase=database_initialization,
            name="Creating README table...",
            func=self.alembic_manager.run_alembic_migration,
            message="Creating README table"
        )

        self.console.add_action(
            phase=database_initialization,
            name="Copying over chat_message.py model",
            func=self.alembic_manager.copy_sqlalchemy_models,
            migration_epoch_key='chat_message_migration_epoch'
        )

        self.console.add_action(
            phase=database_initialization,
            name="Creating ChatMessage table...",
            func=self.alembic_manager.run_alembic_migration,
            message="Creating ChatMessage table"
        )


        self.console.add_action(
            phase=database_initialization,
            name="Saving workspace details to workspace database",
            func=self.save_workspace_details
        )

        self.console.run_workflow(blitzkrieg_initialization_process)

    def find_workspace_directory_names_in_current_directory(self, app):
        workspace_directory_names = []
        # check if there are any directories in the current directory that have a .blitz.env file
        for directory in os.listdir(self.cwd):
            if os.path.isdir(directory):
                if os.path.exists(f"{directory}/.blitz.env"):
                    workspace_directory_names.append(directory)

        return workspace_directory_names

    def teardown_workspace(self, app):
        workspace_directory_names = self.find_workspace_directory_names_in_current_directory(app)
        if not workspace_directory_names:
            workspace_directory_names = ['alexfigueroa']
        workspace_directory_name_select= questionary.select(
            "Select the workspace you want to teardown",
            choices=workspace_directory_names
        ).ask()
        self.workspace_name = workspace_directory_name_select

        if not workspace_directory_names:
            app.handle_error("No workspace found in the current directory")
            return


        # app.display_phase("Teardown Workspace")
        app.handle_info("Removing Workspace Postgres Database...")
        self.workspace_db_manager.teardown(app)
        self.docker_manager.remove_container(app, self.pgadmin_manager.container_name)
        self.docker_manager.remove_all_volumes(app)
        self.docker_manager.remove_docker_network(app, self.docker_network_name)
        self.workspace_directory_manager.teardown(app)

    def save_workspace_details(self):
        self.workspace_db_manager.save_workspace_details()

    def store_credentials(self, postgres_port):
        try:
            workspace_env_vars = [
                ("POSTGRES_USER", self.workspace_db_manager.db_user),
                ("POSTGRES_DB", self.workspace_name),
                ("POSTGRES_HOST", self.workspace_db_manager.container_name),
                ("POSTGRES_PORT", postgres_port),
                ("PGADMIN_PORT", self.pgadmin_port),
                ("WORKSPACE_NAME", self.workspace_name),
                ("WORKSPACE_DIRECTORY", self.workspace_directory_manager.workspace_path),
                ("SQLALCHEMY_MODELS_PATH", self.alembic_manager.sqlalchemy_models_path),
                ("SQLALCHEMY_URI", self.workspace_db_manager.get_sqlalchemy_uri()),
                ("POSTGRES_SERVER_CONFIG_HOST", self.pgadmin_manager.postgres_server_config_host),
                ("POSTGRES_SERVER_CONFIG_USERNAME", self.pgadmin_manager.postgres_server_config_username),
                ("PGADMIN_BINDING_CONFIG_PATH", self.pgadmin_manager.pgadmin_binding_config_path)
            ]

            for var, val in workspace_env_vars:
                self.blitz_env_manager.set_workspace_env_var(var, val)
        except Exception as e:
            self.console.handle_error(f"An error occurred while storing workspace credentials: {e}")



    def add_color(self, text, color):
        colors = {
            "blue": "\033[94m",
            "green": "\033[92m",
            "red": "\033[91m",
            "end": "\033[0m",
        }
        return f"{colors[color]}{text}{colors['end']}"

    def show_workspace_details(self):
        with open(f"{self.workspace_directory_manager.workspace_path}/.env", "r") as f:
            content = f.readlines()

        table = PrettyTable()
        table.field_names = [self.add_color("Variable", "blue"), self.add_color("Value", "green")]
        table.align = "l"  # Align the text to the left

        for line in content:
            if "=" in line:
                var, val = line.strip().split('=', 1)
                table.add_row([var, self.add_color(val, "red")])

        print(table)
