# enum for project types
from enum import Enum as PyEnum

class ProjectTypesEnum(PyEnum):
    PYTHON_CLI = 'python_cli'
    PYO3_RUST_EXTENSION = 'pyo3_rust_extension'
    DJANGO_FASTAPI_REACT_WEB_APPLICATION = 'django_fastapi_react_web_application'
    HYPERMODERN_PYTHON = 'hypermodern_python'
    GOLANG_CLI = 'golang_cli'
    FLASK_RESTFUL = 'flask_restful'
    REPRODUCIBLE_SCIENCE = 'reproducible_science'
    DJANGO_SHOP = 'django_shop'
    DATA_SCIENCE_STACK = 'data_science_stack'
    DJANGO_SAAS = 'django_saas'
    SWIFT_PROJECT = 'swift_project'
    PYQT5_GUI = 'pyqt5_gui'
