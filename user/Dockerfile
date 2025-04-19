FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY ./user/ .
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["uvicorn", "/user/main:app", "--host", "0.0.0.0", "--port", "8001"]