from .user_input import get_pgadmin_credentials, get_postgres_password
from ..core.manager import DockerManager, PostgreSQLManager, PgAdminManager
from .ui import print_message, show_progress, print_header, show_spinner, print_success, print_warning

def initialize_docker():
    print_header("Docker Initialization")
    docker = DockerManager()
    if not docker.is_installed():
        with show_progress("Installing Docker...") as progress:
            docker.install()
            progress.update(100)
        print_success("Docker installed successfully!")
    else:
        print_success("Docker is already installed.")
    return docker

def initialize_postgresql(docker, project_name):
    print_header("PostgreSQL Initialization")
    pg_password = get_postgres_password()
    docker.pull_image("postgres:latest")

    container_name = f"{project_name}-postgres"
    if docker.container_exists(container_name):
        print_warning(f"Container with name {container_name} already exists. Stopping and removing...")
        docker.remove_container(container_name)

    postgres = PostgreSQLManager(container_name)
    print_message(f"Starting container {container_name}...")
    used_port = postgres.start_container(pg_password)
    print_success(f"PostgreSQL is now running on port {used_port}.")

    print_message("Waiting for PostgreSQL to be ready...")
    with show_spinner("Connecting to PostgreSQL..."):
        postgres.wait_for_ready()
    postgres.setup_database(project_name)

    return postgres, pg_password

def initialize_pgadmin(project_name):
    print_header("PgAdmin Initialization")
    pgadmin = PgAdminManager(project_name)
    if pgadmin.container_exists():
        print_message("pgAdmin container already exists. Stopping and removing...", style="bold yellow")
        pgadmin.remove_container()

    pgadmin_email, pgadmin_password = get_pgadmin_credentials()
    print_message("Starting pgAdmin container...")
    pgadmin.start_container(pgadmin_email, pgadmin_password)
    print_success(f"pgAdmin is now running. Access it at http://localhost using the email and password provided.")

    return pgadmin
