from sqlalchemy import create_engine, text
from alembic import context, op
import logging
import os
import sys
from blitzkrieg.db.models.base import Base
from dotenv import load_dotenv  # Ensure this is imported

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.blitz.env'))

sys.path.append(".")

logger = logging.getLogger(__name__)

# Reflect the metadata
metadata = Base.metadata

# Retrieve and validate environment variables
workspace_name = os.getenv('WORKSPACE_NAME')
postgres_port = os.getenv('POSTGRES_PORT')

if not workspace_name or not postgres_port:
    logger.error("Environment variables WORKSPACE_NAME and POSTGRES_PORT must be set.")
    sys.exit(1)

try:
    postgres_port = int(postgres_port)
except ValueError:
    logger.error(f"POSTGRES_PORT must be an integer. Current value: {postgres_port}")
    sys.exit(1)

url = f'postgresql+psycopg2://{workspace_name}-db-user:pw@localhost:{postgres_port}/{workspace_name}'
config = context.config
config.set_main_option('sqlalchemy.url', url)

# Replace 'myapp.models' with the actual path to your models
target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and object.schema == "project_management":
        return True
    return False

def create_schemas(connection):
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS project_management'))
    connection.commit()  # Ensure the schema creation is committed
    print('Created schema: project_management')

def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(url)
    with connectable.connect() as connection:
        try:
            create_schemas(connection)  # Create necessary schemas before running migrations
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_object=include_object,
                include_schemas=True,
                compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
        except Exception as e:
            logging.error("Error during migration: %s", str(e))
            raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
