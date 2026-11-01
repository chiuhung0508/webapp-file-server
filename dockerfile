# Use an official Python base image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /webapp

# Copy dependency list and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files (app, certs, data, run.py, etc.) into the container
COPY . .

# Expose the port your webapp listens on (change 7443 if your app uses a different port)
EXPOSE 7443

# Execute the main application file
CMD ["python", "run.py"]
