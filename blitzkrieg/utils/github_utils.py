import json
import os
from typing import Dict, List
from urllib.parse import urlparse

import requests
import questionary
import click
from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.db.models.project import Project
from blitzkrieg.db.models.readme import Readme
from blitzkrieg.ui_management.console_instance import console
from blitzkrieg.utils.run_command import run_command

def load_github_token() -> str:
    """Load or prompt for GitHub token."""
    github_token = blitz_env_manager.get_global_env_var('GITHUB_TOKEN')
    if not github_token:
        github_token = click.prompt("Enter your GitHub Authentication token")
        blitz_env_manager.set_global_env_var('GITHUB_TOKEN', github_token)
    return github_token

def create_github_repo(project: Project) -> None:
    """Create a new GitHub repository."""
    github_token = load_github_token()
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": project.name,
        "description": project.description,
        "private": False
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 201:
        repo_url = response.json()['html_url']
        project.github_repo = repo_url
        console.handle_success(f'Successfully created repository "{project.name}"')
        console.handle_info(f'You can access it at {repo_url}')
    elif response.status_code == 422:
        console.handle_error(f'Repository "{project.name}" already exists')
    elif response.status_code == 403:
        console.handle_error('Permission denied. Check your GitHub token')
    else:
        console.handle_error(f'Failed to create repository "{project.name}". Status code: {response.status_code}')

def push_project_to_repo(project: Project) -> None:
    """Push a project to its GitHub repository."""
    workspace_dir_path = blitz_env_manager.get_active_workspace_dir()
    project_dir_path = os.path.join(workspace_dir_path, 'projects', project.name)

    github_token = load_github_token()
    parsed_url = urlparse(project.github_repo)
    repo_url = f"https://{github_token}@{parsed_url.netloc}{parsed_url.path}.git"

    try:
        console.handle_wait(f"Initializing git within the project directory: {project_dir_path}")
        run_command(f'cd {project_dir_path} && git init')
        run_command(f'cd {project_dir_path} && git add .')
        run_command(f'cd {project_dir_path} && git commit -m "Initial commit"')
        run_command(f'cd {project_dir_path} && git branch -M master')
        run_command(f'cd {project_dir_path} && git remote add origin {repo_url}')
        run_command(f'cd {project_dir_path} && git push -u origin master')
        console.handle_success(f"Successfully pushed project to GitHub")
    except Exception as e:
        console.handle_error(f"An error occurred while initializing git within the project directory: {str(e)}")

def get_all_github_repo_details_associated_with_user() -> List[Dict]:
    """Get details of all repositories associated with the authenticated user."""
    github_token = load_github_token()
    github_username = blitz_env_manager.get_global_env_var('GITHUB_USERNAME')
    if not github_username:
        github_username = questionary.text("Enter your GitHub username").ask()
        blitz_env_manager.set_global_env_var('GITHUB_USERNAME', github_username)

    url = f"https://api.github.com/users/{github_username}/repos"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    console.handle_wait(f"Getting all repositories associated with user '{github_username}'")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return [
            {
                "name": repo["name"],
                "description": repo["description"],
                "url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "open_issues": repo["open_issues_count"],
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"]
            }
            for repo in response.json()
        ]
    elif response.status_code == 404:
        console.handle_error(f"User '{github_username}' not found")
    elif response.status_code == 403:
        console.handle_error("Permission denied. Check your GitHub token")
    else:
        console.handle_error(f"Failed to get repositories. Status code: {response.status_code}")

    return None

def get_github_username() -> str:
    """Get the GitHub username of the authenticated user."""
    github_username = blitz_env_manager.get_global_env_var('GITHUB_USERNAME')
    if not github_username:
        github_username = questionary.text("Enter your GitHub username").ask()
        blitz_env_manager.set_global_env_var('GITHUB_USERNAME', github_username)
    return github_username

def get_github_repo_readme(session, project: Project, github_username: str) -> str:
    project_name = project.name
    headers = get_github_auth_headers()
    try:
        # get repo readme

        readme_url = f"https://api.github.com/repos/{github_username}/{project_name}/readme"
        readme_response = requests.get(readme_url, headers=headers)
        readme_content = None
        readme_file_path = None
        if readme_response.status_code == 200:
            readme_content = readme_response.json()
            readme_file_path = os.path.join(os.getcwd(), f"{project_name}_README.md")
            with open(readme_file_path, "wb") as f:
                f.write(requests.get(readme_content["download_url"]).content)
                readme = Readme(
                    project_id=project.id,
                    content=readme_content["content"],
                    file_path=readme_file_path,
                    file_name="README"
                )
                session.add(readme)
                try:
                    session.commit()
                    console.handle_success(f"Successfully fetched and saved README for project: {project_name}")
                    return readme
                except Exception as e:
                    session.rollback()
                    console.handle_error(f"An error occurred while saving README to the database: {str(e)}. We had to rollback the transaction.")
                    return None
        else:
            # break the app and throw an error
            console.handle_error(f"Failed to fetch README for repository '{project_name}'")
            # break the app
            return None
    except Exception as e:
        console.handle_error(f"Failed to fetch README for repository '{project_name}': {str(e)}")
        return None

def get_github_auth_headers():
    github_token = load_github_token()
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    return headers
def get_github_repo_details(repo_url: str = None) -> Dict:
    """Get details of a specific GitHub repository."""
    if repo_url:
        parsed_url = urlparse(repo_url)
        project_name = os.path.basename(parsed_url.path)
        github_username = os.path.basename(os.path.dirname(parsed_url.path))
    else:
        project_name = questionary.text("Enter the name of the repository").ask()
        github_username = blitz_env_manager.get_global_env_var('GITHUB_USERNAME')
        if not github_username:
            github_username = questionary.text("Enter your GitHub username").ask()
            blitz_env_manager.set_global_env_var('GITHUB_USERNAME', github_username)

    url = f"https://api.github.com/repos/{github_username}/{project_name}"
    headers = get_github_auth_headers()

    console.handle_wait(f"Getting details for repository '{project_name}'")
    response = requests.get(url, headers=headers)


    if response.status_code == 200:
        repo_details = response.json()
        return {
            "name": repo_details["name"],
            "description": repo_details["description"],
            "url": repo_details["html_url"],
            "stars": repo_details["stargazers_count"],
            "forks": repo_details["forks_count"],
            "open_issues": repo_details["open_issues_count"],
            "created_at": repo_details["created_at"],
            "updated_at": repo_details["updated_at"]
        }
    elif response.status_code == 404:
        console.handle_error(f"Repository '{project_name}' not found")
    elif response.status_code == 403:
        console.handle_error("Permission denied. Check your GitHub token")
    else:
        console.handle_error(f"Failed to get repository details. Status code: {response.status_code}")

    return None

def clone_github_repo(repo_url: str) -> None:
    """Clone a GitHub repository."""
    workspace_dir_path = blitz_env_manager.get_active_workspace_dir()
    workspace_name = os.path.basename(workspace_dir_path)
    run_command(f"cd {workspace_name}/projects && git clone {repo_url}")

def get_repo_issues(repo_url: str) -> List[Dict]:
    """Fetch all issues for a given repository."""
    github_token = load_github_token()
    parsed_url = urlparse(repo_url)
    project_name = os.path.basename(parsed_url.path)
    github_username = os.path.basename(os.path.dirname(parsed_url.path))

    url = f"https://api.github.com/repos/{github_username}/{project_name}/issues"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    console.handle_wait(f"Fetching issues for repository '{project_name}'")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        console.handle_error(f"Failed to fetch issues. Status code: {response.status_code}")
        return []

def get_repo_pull_requests(repo_url: str) -> List[Dict]:
    """Fetch all pull requests for a given repository."""
    github_token = load_github_token()
    parsed_url = urlparse(repo_url)
    project_name = os.path.basename(parsed_url.path)
    github_username = os.path.basename(os.path.dirname(parsed_url.path))

    url = f"https://api.github.com/repos/{github_username}/{project_name}/pulls"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    console.handle_wait(f"Fetching pull requests for repository '{project_name}'")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        console.handle_error(f"Failed to fetch pull requests. Status code: {response.status_code}")
        return []
