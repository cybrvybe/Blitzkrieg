
from blitzkrieg.alembic_manager import AlembicManager
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.class_instances.docker_manager import docker_manager
from blitzkrieg.db.models.base import Base
from blitzkrieg.db.models.environment_variable import EnvironmentVariable
from blitzkrieg.db.models.workspace import Workspace
from blitzkrieg.pgadmin_manager import PgAdminManager
from blitzkrieg.utils.run_command import run_command, run_poetry_command
import time
from blitzkrieg.ui_management.console_instance import console
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import uuid


import os

from blitzkrieg.workspace_directory_manager import WorkspaceDirectoryManager
class WorkspaceDbManager:
    def __init__(
            self,
            port,
            workspace_name: str = None,
    ):
        self.workspace_name = workspace_name
        self.blitz_env_manager = blitz_env_manager
        self.db_user = f"{self.workspace_name}-db-user"
        self.db_port = port
        self.network_name = f"{self.workspace_name}-network"
        self.container_name = f"{self.workspace_name}-postgres"
        self.image_name = "postgres:latest"
        self.console_interface = console
        self.docker_manager = docker_manager
        self.pgadmin_manager: PgAdminManager = None
        self.workspace_directory_manager: WorkspaceDirectoryManager = None
        self.alembic_manager: AlembicManager = None
        self.connection = None
        self.Session = None

    def set_workspace_directory_manager(self, workspace_directory_manager: WorkspaceDirectoryManager):
        self.workspace_directory_manager = workspace_directory_manager

    def set_alembic_manager(self, alembic_manager: AlembicManager):
        self.alembic_manager = alembic_manager

    def set_pgadmin_manager(self, pgadmin_manager: PgAdminManager):
        self.pgadmin_manager = pgadmin_manager

    def set_connection(self):
        engine = sqlalchemy.create_engine(f"postgresql+psycopg2://{self.workspace_name}-db-user:pw@localhost:{self.pgadmin_manager.postgres_port}/{self.workspace_name}")
        self.connection = engine.connect()
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)

    def save_workspace_details(self):
        if not self.connection:
            self.set_connection()

        session = self.Session()

        # Generate workspace_id using uuid4
        workspace_id = uuid.uuid4()

        # Create and save workspace
        workspace = Workspace(
            id=workspace_id,
            name=self.workspace_name,
            description="",
            path=os.path.join(os.getcwd(), self.workspace_name)
        )
        session.add(workspace)
        session.commit()

        pw = blitz_env_manager.get_global_env_var('PASSWORD')

        # Save environment variables
        env_vars = {
            "POSTGRES_USER": self.db_user,
            "POSTGRES_PASSWORD": pw,
            "POSTGRES_DB": self.workspace_name,
            "POSTGRES_HOST": self.container_name,
            "POSTGRES_PORT": self.db_port,
            "PGADMIN_DEFAULT_EMAIL": self.blitz_env_manager.set_global_env_var('EMAIL', 'Enter your email: '),
            "PGADMIN_DEFAULT_PASSWORD": pw,
            "PGADMIN_PORT": self.pgadmin_manager.pgadmin_port,
            "WORKSPACE_NAME": self.workspace_name,
            "WORKSPACE_DIRECTORY": self.workspace_directory_manager.workspace_path,
            "SQLALCHEMY_MODELS_PATH": self.alembic_manager.sqlalchemy_models_path,
            "SQLALCHEMY_URI": self.get_sqlalchemy_uri(),
            "POSTGRES_SERVER_CONFIG_HOST": self.pgadmin_manager.postgres_server_config_host,
            "POSTGRES_SERVER_CONFIG_USERNAME": self.pgadmin_manager.postgres_server_config_username,
            "PGADMIN_BINDING_CONFIG_PATH": self.pgadmin_manager.pgadmin_binding_config_path
        }

        for key, value in env_vars.items():
            env_var_id = uuid.uuid4()
            env_var = EnvironmentVariable(workspace_id=workspace.id, name=key, value=value, id=env_var_id)
            session.add(env_var)

        session.commit()
        session.close()

    def initialize(self):
        self.run_postgres_container()
        self.check_postgres_password()

    def test_sqlalchemy_postgres_connection(self):
        # Replace with your actual connection string
        engine = sqlalchemy.create_engine(self.get_sqlalchemy_uri())
        try:
            connection = engine.connect()
            print("Database connection was successful!")
            print(connection.execute(sqlalchemy.text("SELECT 1")).scalar())  # Executes a simple query to fetch '1'
        except Exception as e:
            print("Error connecting to the database: ", str(e))
        finally:
            if connection:
                connection.close()

    def teardown(self, app):
        return self.docker_manager.remove_container(app, self.container_name)

    def run_postgres_container(self):
        try:
            env_vars = {
                "POSTGRES_DB": self.workspace_name,
                "POSTGRES_USER": self.db_user,
                "POSTGRES_PASSWORD": self.blitz_env_manager.get_global_env_var('PASSWORD'),
                "POSTGRES_INITDB_ARGS": "--auth-local=md5"
            }
            self.docker_manager.run_container(
                container_name=self.container_name,
                image_name=self.image_name,
                network_name=self.network_name,
                env_vars=env_vars,
                ports={self.db_port: self.db_port},
                volumes={},
                detach=True
            )
            return True
        except Exception as e:
            self.console_interface.handle_error(f"Failed to run PostgreSQL container: {str(e)}")
            return False

    def check_postgres_password(self):
        try:
            time.sleep(1.5)
            connection = self.get_connection_details()
            self.console_interface.spinner.text = (f"Trying to connect to SQLAlchemy engine with password ({self.blitz_env_manager.get_global_env_var('PASSWORD')}) at {self.get_sqlalchemy_uri()}")
            engine = sqlalchemy.create_engine(self.get_sqlalchemy_uri())
            connection = engine.connect()
            connection.close()
        except Exception as e:
            self.console_interface.handle_error(f"Failed to connect to PostgreSQL during the verification of Postgres password: {str(e)}")
            return False

    def get_connection_details(self):
        return {
            "database": self.workspace_name,
            "user": self.db_user,
            "password": self.blitz_env_manager.get_global_env_var('PASSWORD'),
            "host": self.container_name,
            "port": self.db_port
        }

    def get_sqlalchemy_uri(self):
        db_uri = f"postgresql+psycopg2://{self.db_user}:{self.blitz_env_manager.get_global_env_var('PASSWORD')}@{self.workspace_name}-postgres:{self.db_port}/{self.workspace_name}"
        return db_uri

    def setup_schema(self):
        self.console_interface.display_step("Database Schema Initialization")
        self.run_alembic_upgrade()

    def run_alembic_upgrade(self):
        command = ['alembic', 'upgrade', 'head']
        result = run_poetry_command(command, self.workspace_directory_manager.workspace_path)
        return result
