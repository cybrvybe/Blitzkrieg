from enum import Enum

class CodeActionTypeEnum(Enum):
    RUN_CLI_COMMAND = 'run_cli_command'
    RUN_PYTHON_SCRIPT = 'run_python_script'
    RUN_RUST_SCRIPT = 'run_rust_script'
    RUN_PYTHON_FUNCTION = 'run_python_function'
    RUN_RUST_FUNCTION = 'run_rust_function',
    BUILD_DOCKER_IMAGE = 'build_docker_image'
    BUILD_DOCKER_CONTAINER = 'build_docker_container'
    RUN_DOCKER_CONTAINER = 'run_docker_container'
    CREATE_GIT_REPOSITORY = 'create_git_repository'
    CREATE_GIT_BRANCH = 'create_git_branch'
    CREATE_GIT_TAG = 'create_git_tag'
    CREATE_GIT_COMMIT = 'create_git_commit'
    CREATE_GIT_REMOTE = 'create_git_remote'
    CREATE_GITHUB_REPOSITORY = 'create_github_repository'
    RELEASE_TO_PYPI = 'release_to_pypi'
    TERMINAL_INPUT = 'terminal_input'
    TERMINAL_OUTPUT = 'terminal_output'
