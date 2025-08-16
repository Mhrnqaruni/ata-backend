# ---- Use a single-stage build for simplicity and robustness ----

# Use the official Python 3.10 image to match the local development environment.
FROM python:3.10-slim-bookworm

# Set the working directory in the container.
WORKDIR /usr/src/app

# Set environment variables to prevent Python from writing .pyc files and to ensure
# output is sent straight to the container logs without buffering.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERed 1

# Upgrade pip to the latest version.
RUN pip install --upgrade pip

# Copy the requirements file.
COPY requirements.txt .

# Install all Python dependencies directly. This is the most reliable method.
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user to run the application for enhanced security.
RUN useradd --create-home appuser

# Copy the application source code from your local machine into the container.
COPY ./app ./app
COPY ./Books ./Books

# Change the ownership of all application files to the non-root user.
RUN chown -R appuser:appuser /usr/src/app

# Switch the active user from root to the new, non-privileged user.
USER appuser

# Expose the port. Railway will automatically map its public-facing port to the
# value of the $PORT environment variable inside the container.
EXPOSE $PORT

# The command to run the application in production.
CMD gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:$PORT app.main:app