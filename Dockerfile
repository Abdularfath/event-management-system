# Use Python 3.11 slim — a minimal Linux image with Python pre-installed
FROM python:3.11-slim
 
# Set the working directory inside the container
# All subsequent commands run from this folder
WORKDIR /app
 
# Copy requirements.txt first (before the rest of the code)
# Docker caches this layer — if requirements.txt hasn't changed,
# it skips the pip install step on rebuilds (saves time)
COPY requirements.txt .
 
# Install all Python libraries listed in requirements.txt
# --no-cache-dir keeps the image smaller
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy all project files into the container's /app folder
COPY . .
 
# Tell Docker that the app listens on port 5000
# (this is documentation only — the actual port mapping is in docker-compose.yml)
EXPOSE 5000
 
# The command that runs when the container starts
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "wsgi:application"]