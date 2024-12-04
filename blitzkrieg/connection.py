from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from blitzkrieg.class_instances.blitz_env_manager import blitz_env_manager
from blitzkrieg.db.models.project import Project

def get_db_engine():
    workspace_name = blitz_env_manager.get_workspace_env_var('WORKSPACE_NAME')
    engine = create_engine(f'postgresql+psycopg2://{workspace_name}-db-user:pw@localhost:5432/{workspace_name}')
    return engine

def get_docker_db_engine():
    postgres_port = blitz_env_manager.get_workspace_env_var('POSTGRES_PORT')
    workspace_name = blitz_env_manager.get_workspace_env_var('WORKSPACE_NAME')
    engine = create_engine(f"postgresql+psycopg2://{workspace_name}-db-user:pw@host.docker.internal:{str(postgres_port)}/{workspace_name}")
    return engine

def get_docker_db_session():
    engine = get_docker_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def get_db_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def close_db_session(session):
    if session:
        session.close()

def execute_db_operation(engine, operation):
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            connection.execute(text(operation))
            trans.commit()
        except SQLAlchemyError as e:
            trans.rollback()
            print(f"An error occurred in execute_db_operation: {e}")

def get_project_by_name(project_name, session):
    project = session.query(Project).filter(Project.name == project_name).first()
    return project

def save_project(project, session):
    session.add(project)
    session.commit()
