FROM python:3.11-slim

WORKDIR /app

# Install requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY backend/ ./

# Expose port
ENV PORT=8000
EXPOSE 8000

# Run the server
CMD ["python3", "app/main.py"]
