import click
import questionary
import subprocess
from sqlalchemy import text
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.db.models.readme import Readme
from blitzkrieg.utils.llm_utils import summarize_project
from blitzkrieg.workspace_manager import WorkspaceManager
from blitzkrieg.ui_management.console_instance import console
from blitzkrieg.db.models.project import Project
from blitzkrieg.enums.project_types_enum import ProjectTypesEnum
from blitzkrieg.connection import get_docker_db_session, save_project
from blitzkrieg.ui_management.tui import run_tui
from blitzkrieg.utils.github_utils import clone_github_repo, create_github_repo, get_github_repo_details, get_all_github_repo_details_associated_with_user, get_github_repo_readme, get_github_username, get_repo_pull_requests, push_project_to_repo
from blitzkrieg.utils.project_tracking_utils import save_project_by_repo, save_pull_requests
from blitzkrieg.cookie_cutter_manager import CookieCutterManager
from blitzkrieg.utils.validation_utils import validate_package_installation, validate_version_number
from blitzkrieg.utils.poetry_utils import initialize_poetry, update_project_version, install_project_dependencies, build_project_package
from blitzkrieg.utils.git_utils import authenticate_github_cli, stage_files_for_commit, commit_staged_files, create_git_tag, sync_local_changes_to_remote_repository
import rust_codetextualizer
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer
from textual.containers import Container
from textual import events

@click.group()
def main():
    pass

@main.group()
def workspace():
    """Commands for managing workspaces."""
    pass

@workspace.command('create')
@click.argument("workspace_name")
def workspace_create(workspace_name):
    """Create a new workspace."""
    WorkspaceManager(workspace_name=workspace_name).blitz_init()

@workspace.command('delete')
@click.argument("workspace_name")
def workspace_delete(workspace_name, app=None):
    """Delete a workspace and perform any necessary cleanup."""
    if app is None:
        app = console
    WorkspaceManager(workspace_name=workspace_name).teardown_workspace(app)

@workspace.command('set')
def workspace_set():
    """Set the current workspace."""
    workspace_name = questionary.text("Enter the name of the workspace:").ask()
    blitz_env_manager.set_global_env_var('CURRENT_WORKSPACE', workspace_name)

@main.group()
def project():
    """Commands for managing projects."""
    pass

@project.command('create')
def project_create():
    """Create a new project within the current workspace."""
    project_types = [
        {'name': pt.name.replace('_', ' ').title(), 'value': pt}
        for pt in ProjectTypesEnum
    ]

    project_type = questionary.select(
        "Select project type:",
        choices=project_types
    ).ask()

    project_name = questionary.text("Enter the project name:").ask()
    short_description = questionary.text("Enter a short description for the project (roughly 3-5 words):").ask()
    description = questionary.text("Enter a detailed description for the project:").ask()

    project = Project(
        name=project_name,
        project_type=project_type,
        short_description=short_description,
        description=description
    )

    try:
        session = get_docker_db_session()
        console.handle_info(f"Starting the create_project command. About to initialize the CookieCutterManager")
        cookie_cutter_manager = CookieCutterManager()
        console.handle_info(f"CookieCutterManager initialized successfully")
        console.handle_info(f"About to get the template path for the project type: {project_type.name}")
        template_path = cookie_cutter_manager.get_template_path(project_type)
        console.handle_info(f"Template path retrieved successfully: {template_path}")
        console.handle_info(f"About to generate the project")
        cookie_cutter_manager.generate_project(
            template_path=template_path,
            project=project
        )
        console.handle_success(f"Successfully created project: {project_name}")
        console.handle_info(f"About to create a GitHub repo")
        create_github_repo(project)
        save_project(project, session)
        console.handle_success(f"Successfully created a GitHub repository for the project: {project_name}")
        push_project_to_repo(project)
    except Exception as e:
        console.handle_error(f"An error occurred while creating the project: {str(e)}")

@project.command('track')
@click.option('--repo_url', prompt='Enter the project repository URL', help='The URL of the project repository')
def project_track(repo_url):
    """Track a project within the current workspace."""
    if repo_url:
        project_github_repo_details = get_github_repo_details(repo_url)
    else:
        project_github_repo_details = get_github_repo_details()

    project_name = project_github_repo_details['name']

    if repo_url:
        project_github_repo_details['url'] = repo_url

    project = Project(
        name=project_name,
        github_repo=project_github_repo_details['url'],
        description=project_github_repo_details['description']
    )

    github_username = get_github_username()
    try:
        session = get_docker_db_session()
        save_project(project, session)
        get_github_repo_readme(
            session,
            project,
            github_username

        )
        console.handle_success(f"Successfully tracked project: {project_name}")
    except Exception as e:
        console.handle_error(f"An error occurred while tracking the project: {str(e)}")

    clone_github_repo(project_github_repo_details['url'])

@project.command('untrack')
def project_untrack():
    """Untrack projects within the current workspace."""
    session = get_docker_db_session()
    projects = session.query(Project).all()

    if not projects:
        console.handle_error("No projects found in the database.")
        return

    project_choices = [{'name': project.name, 'value': project} for project in projects]
    projects_to_untrack = questionary.checkbox(
        "Select projects to untrack:",
        choices=project_choices
    ).ask()

    if not projects_to_untrack:
        console.handle_error("No projects selected. Exiting.")
        return

    for project in projects_to_untrack:
        try:
            session.delete(project)
            session.commit()
            console.handle_success(f"Successfully untracked project: {project.name}")
        except Exception as e:
            console.handle_error(f"An error occurred while untracking the project: {str(e)}")

@project.command('track-multiple')
def project_track_multiple():
    """Track multiple predefined projects within the current workspace."""
    github_repo_urls = [
        'https://github.com/ytdl-org/youtube-dl',
        'https://github.com/openai/whisper',
        'https://github.com/3b1b/manim',
        'https://github.com/sherlock-project/sherlock'
    ]

    for repo_url in github_repo_urls:
        project_github_repo_details = get_github_repo_details(repo_url)
        project_name = project_github_repo_details['name']
        project_github_repo_details['url'] = repo_url

        project = Project(
            name=project_name,
            github_repo=project_github_repo_details['url'],
            description=project_github_repo_details['description']
        )

        try:
            session = get_docker_db_session()
            save_project(project, session)
            console.handle_success(f"Successfully tracked project: {project_name}")
        except Exception as e:
            console.handle_error(f"An error occurred while tracking the project: {str(e)}")

        clone_github_repo(project_github_repo_details['url'])

@project.command('track-my-github')
def project_track_my_github():
    """Track all GitHub projects owned by the authenticated user."""
    github_repos = get_all_github_repo_details_associated_with_user()
    session = get_docker_db_session()

    for repo in github_repos:
        project = save_project_by_repo(session, repo)
        pull_requests = get_repo_pull_requests(repo['url'])
        save_pull_requests(session, pull_requests, project)
        clone_github_repo(repo['url'])

@main.group()
def env():
    """Commands for managing environment variables."""
    pass

@env.command('set')
def env_set():
    """Set a global environment variable."""
    env_var_name = questionary.text("Enter the name of the environment variable:").ask()
    env_var_value = questionary.text("Enter the value of the environment variable:").ask()
    blitz_env_manager.set_global_env_var(env_var_name, env_var_value)

@env.command('delete')
def env_delete():
    """Delete a global environment variable."""
    blitz_env_manager.delete_global_env_var()

@env.command('view')
def env_view():
    """View all global environment variables."""
    global_env_vars = blitz_env_manager.get_global_env_vars()
    console.handle_info("Global environment variables:")
    for key, value in global_env_vars.items():
        console.handle_info(f"{key}: {value}")

@main.command('setup-test-env')
def setup_test_env():
    """Set up the test environment."""
    subprocess.run(['../../bash/setup_test_env.sh'], check=True)

@main.command('extract-code-context')
def extract_code_context():
    """Extract code context using the Rust codetextualizer."""
    try:
        console.handle_wait("Starting the contextualization process")
        rust_codetextualizer.extract_code_context('blitz_init')
    except Exception as e:
        console.handle_error(f"An error occurred during contextualization: {str(e)}")

@main.command('release-version')
@click.option('--version', prompt='New version number', help='The new version number for the release')
def release_version(version):
    """Set up Poetry and release a new version of Blitzkrieg to PyPI."""
    validate_version_number(version)

    try:
        poetry_installation_is_successful = validate_package_installation('poetry')

        if not poetry_installation_is_successful:
            console.handle_error("Poetry installation failed. Check the validate_poetry_installation() function.")

        initialize_poetry()
        update_project_version(version)
        install_project_dependencies()
        build_project_package()

        # Check for PyPI credentials
        pypi_username = "__token__"
        pypi_api_key = blitz_env_manager.get_global_env_var('PYPI_API_KEY')
        if not pypi_api_key:
            blitz_env_manager.set_global_env_var('PYPI_API_KEY', click.prompt("Enter your PyPI API key"))
            pypi_api_key = blitz_env_manager.get_global_env_var('PYPI_API_KEY')

        # Publish to PyPI
        subprocess.run(["poetry", "publish", "--username", pypi_username, "--password", pypi_api_key], check=True)

        # Create a git tag for the new version
        stage_files_for_commit(['pyproject.toml'])
        commit_message = f"Bump version to {version}"
        commit_staged_files(commit_message)
        tag_name = f"v{version}"
        create_git_tag(tag_name)
        # Push the new tag and commit to the remote repository using GitHub CLI
        authenticate_github_cli()
        sync_local_changes_to_remote_repository()

        click.echo(f"Successfully set up Poetry and released Blitzkrieg version {version} to PyPI!")
    except subprocess.CalledProcessError as e:
        click.echo(f"An error occurred during the release process: {str(e)}")
    except Exception as e:
        click.echo(f"An unexpected error occurred: {str(e)}")

@main.group()
def ai():
    """Commands for AI-related tasks."""
    pass

@main.command("chat")
def chat():
    """Start a chat session."""
    session = get_docker_db_session()
    project = session.query(Project).where(Project.name == 'Blitzkrieg').first()
    readme = session.query(Readme).where(Readme.project_id == project.id).first()
    readme.content = readme.content.replace('\n', ' ')
    summarize_project(readme.content)

@main.command('launch-interface')
@click.pass_context
def launch_interface(ctx):
    """Launch the Textual User Interface with all available commands."""
    commands = ctx.parent.command.commands.values()
    print('commands: ', commands)
    run_tui(commands)

class TableViewer(App):
    CSS = """
    DataTable {
        height: 1fr;
    }
    """

    def __init__(self, headers, data):
        super().__init__()
        self.headers = headers
        self.data = data

    def compose(self) -> ComposeResult:
        yield Container(DataTable())
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*self.headers)
        for row in self.data:
            table.add_row(*[str(cell) for cell in row])

    def on_key(self, event: events.Key) -> None:
        if event.key in ("q", "Q"):
            self.exit()

@main.command('view-database-tables')
def view_database_tables():
    """View tables in the database."""
    session = get_docker_db_session()

    # Fetch schemas
    schemas = session.execute(text("SELECT schema_name FROM information_schema.schemata")).fetchall()
    if not schemas:
        console.handle_error("No schemas found in the database.")
        return

    # Select schema
    schema_select = questionary.select(
        "Select a schema to view:",
        choices=[schema[0] for schema in schemas]
    ).ask()

    if not schema_select:
        console.handle_error("No schema selected. Exiting.")
        return

    # Fetch tables for the selected schema
    tables = session.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema_select}'")).fetchall()
    if not tables:
        console.handle_error(f"No tables found in the schema '{schema_select}'.")
        return

    # Select table
    table_select = questionary.select(
        "Select a table to view:",
        choices=[table[0] for table in tables]
    ).ask()

    if not table_select:
        console.handle_error("No table selected. Exiting.")
        return

    # Fetch table data
    try:
        result = session.execute(text(f"SELECT * FROM {schema_select}.{table_select}"))
        columns = result.keys()
        table_data = result.fetchall()
    except Exception as e:
        console.handle_error(f"Error fetching data from table '{table_select}': {str(e)}")
        return

    # Display table information
    console.handle_info(f"Table: {table_select}")
    console.handle_info(f"Rows: {len(table_data)}")
    console.handle_info(f"Columns: {len(columns)}")

    if not table_data:
        console.handle_info("The table is empty.")
        return

    # Launch the TUI
    app = TableViewer(columns, table_data)
    app.run()

    console.handle_info("Table view closed. Press Enter to continue...")
    input()

if __name__ == "__main__":
    click.echo("Starting the application...")
    main()
