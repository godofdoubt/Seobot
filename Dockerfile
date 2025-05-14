# Use the latest stable Python runtime (Python 3.11 slim) as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Prevent apt-get from asking questions
ENV DEBIAN_FRONTEND=noninteractive

# Install the dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install Playwright's required system dependencies
# These are necessary for the browsers to run
RUN python -m playwright install-deps chromium

# Install Playwright browsers AFTER installing system dependencies
RUN python -m playwright install chromium

# Copy the rest of your application code into the container
COPY . /app

# Make port 8501 available to the world outside this container (default for Streamlit)
EXPOSE 8501

# Command to run the Streamlit application
CMD ["streamlit", "run", "main.py"]