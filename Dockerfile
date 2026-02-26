# Dockerfile for LangGraph CitiBike SQL Agent

# 1. Base image: python:3.11-slim is lightweight and modern.
FROM python:3.11-slim

# 2. Set working directory in the container
WORKDIR /app

# 3. Copy requirements first to leverage Docker cache.
# If only Python code changes, Docker will not reinstall dependencies on rebuild.
COPY requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . /app

# 6. Expose the port used by Streamlit
EXPOSE 8000

# 7. Command to run the application when the container starts
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8000", "--server.address=0.0.0.0"]