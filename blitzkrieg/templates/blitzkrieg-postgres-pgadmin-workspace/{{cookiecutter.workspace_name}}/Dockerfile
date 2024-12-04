
# Dockerfile for workspace
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the application code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Alembic
RUN pip install alembic

RUN chown -R 1000:1000 /app

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
