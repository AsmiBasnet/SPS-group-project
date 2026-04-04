# ================================================
# PolicyGuard Dockerfile
# Packages the Streamlit app into a container
# Ollama runs separately on the host machine
# ================================================

# Base image — slim Python 3.12 to keep image small
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies needed by PyMuPDF
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# so pip install only re-runs when requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY src/ ./src/
COPY app.py .

# Create folders the app expects at runtime
RUN mkdir -p logs data

# Expose Streamlit default port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
