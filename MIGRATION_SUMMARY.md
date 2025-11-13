# Migration Summary: SQLite → PostgreSQL + Environment Variables

## ✅ Completed Changes

### 1. Database Migration (SQLite → PostgreSQL)
- **models.py**: Completely migrated to PostgreSQL using `psycopg2`
- Changed `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`
- Changed `?` placeholders → `%s` placeholders
- Changed `sqlite3.Row` → `psycopg2.extras.RealDictCursor`
- Updated date functions to PostgreSQL syntax
- Changed `cursor.lastrowid` → `RETURNING id` pattern

### 2. Environment Variables
- **email_sender.py**: Now reads from environment variables first, falls back to JSON
- **app.py**: Uses environment variables for SECRET_KEY, PORT, FLASK_DEBUG
- **models.py**: Uses DATABASE_URL or individual DB_* environment variables

### 3. Security Improvements
- Created `.gitignore` to exclude:
  - `.env` files
  - `email_config.json`
  - Database files
  - Logs
- Created `.env.example` as template

### 4. Dependencies
- Added `psycopg2-binary>=2.9.0` for PostgreSQL
- Added `python-dotenv>=1.0.0` for environment variables

## 📋 Environment Variables Required

### Database
```
DATABASE_URL=postgresql://user:password@host:port/database
# OR
DB_HOST=localhost
DB_PORT=5432
DB_NAME=interac_transfers
DB_USER=postgres
DB_PASSWORD=your-password
```

### Email (SMTP)
```
SMTP_SENDER_EMAIL=your-email@gmail.com
SMTP_SENDER_PASSWORD=your-app-password
SMTP_SENDER_NAME=Interac e-Transfer
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Flask
```
SECRET_KEY=your-secret-key
FLASK_DEBUG=False
PORT=5000
```

## 🚀 Next Steps for Deployment

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in your actual values
   - In CapRover, add these as environment variables

3. **Test locally with PostgreSQL:**
   - Make sure PostgreSQL is running
   - Update `.env` with your local DB credentials
   - Run `python app.py`

4. **Deploy to CapRover:**
   - Install PostgreSQL one-click app
   - Get connection string
   - Set environment variables in CapRover
   - Connect GitHub repo
   - Deploy!

## ⚠️ Important Notes

- **Balance calculation**: Still uses dynamic calculation (no stored balance table needed)
- **Backward compatibility**: Email sender still supports `email_config.json` for local dev
- **Database initialization**: Tables are created automatically on first run
- **No data migration needed**: Fresh start with PostgreSQL

