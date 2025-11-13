# Deployment Guide for CapRover + PostgreSQL

## Prerequisites
- VPS with CapRover installed
- PostgreSQL one-click app installed in CapRover
- GitHub repository with your code

## Step 1: Install PostgreSQL in CapRover
1. In CapRover dashboard, go to "One-Click Apps/Databases"
2. Install PostgreSQL
3. Note down the connection details (host, port, database name, user, password)

## Step 2: Set Environment Variables in CapRover
1. In your app settings in CapRover, go to "App Configs"
2. Add the following environment variables:

```
SECRET_KEY=<generate-a-random-secret-key>
FLASK_DEBUG=False
PORT=80

# Database (use the connection string from PostgreSQL one-click app)
DATABASE_URL=postgresql://postgres:password@postgres:5432/postgres

# Email Configuration
SMTP_SENDER_EMAIL=your-email@gmail.com
SMTP_SENDER_PASSWORD=your-gmail-app-password
SMTP_SENDER_NAME=Interac e-Transfer
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

## Step 3: Deploy from GitHub
1. In CapRover, create a new app
2. Connect your GitHub repository
3. Set the branch (usually `main` or `master`)
4. Set the Dockerfile path (if using custom Dockerfile) or use CapRover's auto-detection

## Step 4: Create Dockerfile (if needed)
If CapRover doesn't auto-detect, create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 80

# Run application
CMD ["python", "app.py"]
```

## Step 5: Database Initialization
The database tables will be automatically created on first run when the app starts.

## Step 6: Verify Deployment
1. Check app logs in CapRover
2. Visit your app URL
3. Test creating a contact and sending a transfer

## Local Development Setup

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your local settings:
- Set up local PostgreSQL connection
- Add your email credentials

3. Install dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

4. Run the app:
```bash
python app.py
```

## Important Notes

- **Never commit `.env` file** - it's in `.gitignore`
- **Never commit `email_config.json`** - use environment variables instead
- The app will automatically create database tables on first run
- Make sure PostgreSQL is running before starting the app

