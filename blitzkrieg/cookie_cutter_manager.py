import os
from cookiecutter.main import cookiecutter
import questionary
from blitzkrieg.db.models.project import Project
from blitzkrieg.enums.project_types_enum import ProjectTypesEnum
from blitzkrieg.ui_management.console_instance import console
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.utils.port_allocation import find_available_port

class CookieCutterManager:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.blitz_env_manager = blitz_env_manager

    def generate_workspace(self, workspace_name: str, postgres_port: int):
        cwd = os.getcwd()
        workspace_path = os.path.join(cwd, workspace_name)
        workspace_template_path = self.get_workspace_template_path()
        blitz_env_manager.set_workspace(workspace_name)
        try:
            cookiecutter(
                workspace_template_path,
                no_input=True,
                extra_context={
                    'workspace_name': workspace_name,
                    'pgadmin_port': find_available_port(5050),
                    'postgres_port': postgres_port,
                    'pgadmin_port_forward': find_available_port(80),
                    'pgadmin_secondary_port': find_available_port(443),
                    'pgadmin_secondary_port_forward': find_available_port(443),
                    'postgres_port_forward': find_available_port(5432)
                },
                output_dir=cwd
            )
            console.handle_success(f"Generated workspace {workspace_name} at {workspace_path}")
        except Exception as e:
            console.handle_error(f"Failed to generate workspace: {str(e)}")


    def generate_project(self, project: Project, template_path):
        try:
            project_name = project.name

            workspace_dir = self.blitz_env_manager.get_active_workspace_dir()
            workspace_projects_dir = os.path.join(workspace_dir, 'projects')

            template_context = self.get_template_context(project)
            cookiecutter(
                template_path,
                no_input=True,
                extra_context=template_context,
                output_dir=workspace_projects_dir
            )
            console.handle_success(f"Generated project {project_name} at {workspace_dir} with the slug {project_name.lower().replace(' ', '_')}")
        except Exception as e:
            console.handle_error(f"Failed to generate project: {str(e)}")

    def get_template_context(self, project: Project):
        project_type = project.project_type
        project_name = project.name
        project_description = project.description
        project_short_description = project.short_description

        project_type_template_name_mapper = {
            ProjectTypesEnum.PYTHON_CLI: {
                'project_name': 'Python CLI',
                'project_slug': 'python_cli',
                'project_description': 'A Python CLI project',
                'author_name': 'Your Name',
                'author_email': ''
            },
            ProjectTypesEnum.PYO3_RUST_EXTENSION: {
                # prompt the user for text input using questionary for project_name value
                'project_name': project_name,
                'project_slug': project_name.lower().replace(' ', '_'),
                'project_description': project_description,
                'full_name': 'Your Name',
                'email': '',
                'project_short_description': project_short_description,
                'github_username': 'alexfigueroa-solutions'
            },
            ProjectTypesEnum.DJANGO_FASTAPI_REACT_WEB_APPLICATION: {
                'github_repository_name': project_name.lower().replace(' ', '-'),
                'app_name': project_name.lower().replace(' ', '_'),
                'email': '',
                'description': project_description,
                'github_username': 'alexfigueroa-solutions',
            }
        }
        return project_type_template_name_mapper.get(project_type)

    def get_workspace_template_path(self):
        return os.path.join(self.template_dir, 'blitzkrieg-postgres-pgadmin-workspace')

    def get_template_path(self, project_type: ProjectTypesEnum):
        # make project_type snake_case
        project_type_template_name_mapper = {
            ProjectTypesEnum.PYTHON_CLI: 'poetry-cli-template',
            ProjectTypesEnum.PYO3_RUST_EXTENSION: 'pyo3-rust-extension-template',
            ProjectTypesEnum.DJANGO_FASTAPI_REACT_WEB_APPLICATION: 'https://github.com/agconti/cookiecutter-django-rest',
            ProjectTypesEnum.HYPERMODERN_PYTHON: 'https://github.com/cjolowicz/cookiecutter-hypermodern-python',
            ProjectTypesEnum.GOLANG_CLI: 'https://github.com/lacion/cookiecutter-golang',
            ProjectTypesEnum.FLASK_RESTFUL: 'https://github.com/karec/cookiecutter-flask-restful',
            ProjectTypesEnum.REPRODUCIBLE_SCIENCE: 'https://github.com/mkrapp/cookiecutter-reproducible-science',
            ProjectTypesEnum.DJANGO_SHOP: 'https://github.com/awesto/cookiecutter-django-shop',
            ProjectTypesEnum.DATA_SCIENCE_STACK: 'https://github.com/jgoerner/data-science-stack-cookiecutter',
            ProjectTypesEnum.DJANGO_SAAS: 'https://github.com/ernestofgonzalez/djangorocket',
            ProjectTypesEnum.SWIFT_PROJECT: 'https://github.com/artemnovichkov/swift-project-template',
            ProjectTypesEnum.PYQT5_GUI: 'https://github.com/artemnovichkov/swift-project-template',
            ProjectTypesEnum.PYO3_RUST_EXTENSION: 'pyo3-rust-extension-template',
        }

        template_name = project_type_template_name_mapper.get(project_type)
        if not template_name:
            raise ValueError(f"Invalid project type: {project_type.name}")
        template_path = os.path.join(self.template_dir, template_name)
        if not os.path.exists(template_path):
            error_message = f"Template for {project_type.name} projects not found. Please ensure the template exists at {template_path}"
            console.handle_error(error_message)
            raise FileNotFoundError(error_message)
        return template_path
