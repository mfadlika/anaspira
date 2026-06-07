FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default port (Render will override this via $PORT)
EXPOSE 8501

# Default command to run the Streamlit app using the wrapper script
CMD ["python", "run_streamlit.py"]
