# ---- STAGE 1: BUILDER (This is now a multi-stage build for better security) ----
# We use a full Debian image here because it has the build tools we need.
FROM python:3.10-bookworm as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev

# Set the working directory
WORKDIR /usr/src/app

# Upgrade pip
RUN pip install --upgrade pip

# Copy only the requirements file to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# ---- STAGE 2: FINAL IMAGE (Slim and Secure) ----
# We start fresh with a slim image for a smaller, more secure final container.
FROM python:3.10-slim-bookworm

# Set the working directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- [THE FIX IS HERE] ---
# Install the RUNTIME system dependencies needed by Tesseract and PyMuPDF.
# We switch to the root user temporarily to do this.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Clean up the apt cache to keep the image size down
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# --- [END OF FIX] ---

# Create a non-root user to run the application
RUN useradd --create-home appuser

# Copy the pre-compiled Python wheels from the builder stage
COPY --from=builder /usr/src/app/wheels /wheels

# Copy the application source code
COPY ./app ./app
COPY ./Books ./Books

# Install the Python dependencies from the local wheels
# This is much faster and doesn't require build tools in the final image.
RUN pip install --no-cache /wheels/*

# Create the directory for assessment uploads
RUN mkdir -p /usr/src/app/assessment_uploads

# Change the ownership of all application files to the non-root user
RUN chown -R appuser:appuser /usr/src/app

# Switch the active user to the new, non-privileged user
USER appuser

# Expose the port (Railway will use the $PORT variable)
EXPOSE 8080

# The command to run the application in production
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8080", "app.main:app"]