FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY ./chat-microservice/ .
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]