# ---- Stage 1: Builder ----
# Use the official Python 3.10 image to match the local development environment.
FROM python:3.10-slim-bookworm as builder

# Set the working directory in the container.
WORKDIR /usr/src/app

# Prevent python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1

# Install system dependencies that might be needed by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Install pip-tools to compile requirements
RUN pip install --upgrade pip
RUN pip install pip-tools

# Copy only the requirements files to leverage Docker cache
COPY requirements.txt .

# Install all Python dependencies into a wheelhouse
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# ---- Stage 2: Runtime ----
# Use the same slim, secure Python 3.10 base image for the final container
FROM python:3.10-slim-bookworm as runtime

WORKDIR /usr/src/app

# Copy the installed dependencies from the builder stage
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .

# Install the dependencies from the wheels
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

# Create a non-root user to run the application for better security
RUN useradd --create-home appuser
USER appuser

# Copy the rest of the application source code
COPY ./app ./app
COPY ./Books ./Books

# Expose the port the app runs on
# The $PORT variable will be automatically provided by Railway
EXPOSE $PORT

# The command to run the application in production using Gunicorn
CMD gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:$PORT app.main:app