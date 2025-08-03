# Use slim Python base image
FROM python:3.10-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the script itself
COPY . .

# Expose the port Cloud Run expects
EXPOSE 8080

# Start your app — assumes it runs a web server!
CMD ["python", "main.py"]
