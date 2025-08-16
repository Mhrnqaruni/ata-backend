# ---- Stage 1: Builder ----
# Use the official Python 3.10 image to match the local development environment.
# This ensures consistency between your local venv and the production container.
FROM python:3.10-slim-bookworm as builder

# Set the working directory in the container.
WORKDIR /usr/src/app

# Set environment variables to prevent Python from writing .pyc files and to ensure
# output is sent straight to the container logs without buffering.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system-level dependencies that might be needed by some Python packages
# during installation (e.g., packages that compile C code).
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Upgrade pip to the latest version.
RUN pip install --upgrade pip

# Copy only the requirements file first. This leverages Docker's layer caching.
# If requirements.txt doesn't change, Docker will reuse this layer, speeding up builds.
COPY requirements.txt .

# Install all Python dependencies. We use 'pip wheel' to pre-compile packages,
# which can make the final installation in the runtime stage faster.
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# ---- Stage 2: Runtime ----
# Use the same slim, secure Python 3.10 base image for the final container.
FROM python:3.10-slim-bookworm as runtime

WORKDIR /usr/src/app

# Copy the pre-compiled wheel dependencies from the builder stage.
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .

# Install the dependencies from the wheels. This is often faster and more reliable
# than installing from scratch in the final image.
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

# Create a non-root user to run the application for enhanced security.
# Running as a limited user is a critical production best practice.
RUN useradd --create-home appuser

# Copy the application source code from your local machine into the container.
COPY ./app ./app
COPY ./Books ./Books

# Change the ownership of all application files to the non-root user.
# This is the CRITICAL FIX for the PermissionError [Errno 13].
RUN chown -R appuser:appuser /usr/src/app

# Switch the active user from root to the new, non-privileged user.
# All subsequent commands will be run by 'appuser'.
USER appuser

# Expose the port. Railway will automatically map its public-facing port to the
# value of the $PORT environment variable inside the container.
EXPOSE $PORT

# The command to run the application in production.
# We use the "shell form" (no square brackets) so that the shell can substitute
# the $PORT environment variable correctly.
# Gunicorn is the process manager, and Uvicorn is the high-speed worker for FastAPI.
CMD gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:$PORT app.main:app