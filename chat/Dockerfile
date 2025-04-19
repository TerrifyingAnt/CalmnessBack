FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY ./chat/ .
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["uvicorn", "/chat/main:app", "--host", "0.0.0.0", "--port", "8000"]