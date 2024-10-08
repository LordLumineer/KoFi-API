# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app/ .

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables (if required)
ENV ENVIRONMENT=production

# Command to run the application with FastAPI
# RUN cd app
CMD ["fastapi", "run", "main.py"]
