from typing import List
import uuid
import questionary
from blitzkrieg.db.models.project import Project
from blitzkrieg.db.models.pull_request import PullRequest
from blitzkrieg.ui_management.console_instance import console
from blitzkrieg.connection import get_docker_db_session, save_project
from blitzkrieg.utils.github_utils import get_github_repo_details, clone_github_repo

def track_single_project(repo_url: str = None) -> None:
    """Track a single project within the current workspace."""
    project_details = get_github_repo_details(repo_url)
    if not project_details:
        return

    project = Project(
        name=project_details['name'],
        github_repo=project_details['url'],
        description=project_details['description']
    )

    save_project_and_clone(project)

def track_multiple_projects(repo_urls: List[str]) -> None:
    """Track multiple projects within the current workspace."""
    for repo_url in repo_urls:
        track_single_project(repo_url)

def untrack_projects() -> None:
    """Untrack multiple projects within the current workspace."""
    session = get_docker_db_session()
    projects = session.query(Project).all()

    if not projects:
        console.handle_error("No projects found in the database.")
        return

    projects_to_untrack = select_projects_to_untrack(projects)

    for project in projects_to_untrack:
        try:
            session.delete(project)
            session.commit()
            console.handle_success(f"Successfully untracked project: {project.name}")
        except Exception as e:
            console.handle_error(f"An error occurred while untracking the project: {str(e)}")

def save_project_and_clone(project: Project) -> None:
    """Save a project to the database and clone its repository."""
    try:
        session = get_docker_db_session()
        save_project(project, session)
        console.handle_success(f"Successfully tracked project: {project.name}")
        clone_github_repo(project.github_repo)
    except Exception as e:
        console.handle_error(f"An error occurred while tracking the project: {str(e)}")

def select_projects_to_untrack(projects: List[Project]) -> List[Project]:
    """Prompt the user to select projects to untrack."""
    project_choices = [{'name': project.name, 'value': project} for project in projects]
    return questionary.checkbox(
        "Select projects to untrack:",
        choices=project_choices
    ).ask()

def save_pull_requests(session, pull_requests, project: Project):
    for pr_data in pull_requests:
        pr = PullRequest(
            project_id=project.id,
            pr_number=pr_data['number'],
            title=pr_data['title'],
            state=pr_data['state'],
            created_at=pr_data['created_at'],
            updated_at=pr_data['updated_at'],
            body=pr_data['body']
        )
        session.add(pr)

    try:
        session.commit()
        console.handle_success(f"Fetched and saved {len(pull_requests)} pull requests for project: {project.name}")
    except Exception as e:
        session.rollback()
        console.handle_error(f"An error occurred while saving pull requests to the database: {str(e)}. We had to rollback the transaction.")

def save_project_by_repo(session, repo):
    project_name = repo['name']
    repo_url = repo['url']
    project = Project(
        id=uuid.uuid4(),
        name=project_name,
        github_repo=repo_url,
        description=repo['description']
    )

    try:
        session.add(project)
        session.commit()
        console.handle_success(f"Successfully saved project: {project_name}")
        return project
    except Exception as e:
        session.rollback()
        console.handle_error(f"An error occurred while saving the project: {str(e)}. We had to rollback the transaction.")
        return None
