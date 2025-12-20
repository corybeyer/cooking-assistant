FROM python:3.12-slim-bookworm

# Install ODBC driver for SQL Server
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (shared modules: config, database, models)
COPY app/ ./app/

# Copy Streamlit app
COPY streamlit_app.py .

# Expose port
EXPOSE 80

# Run Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=80", "--server.address=0.0.0.0", "--server.headless=true"]
