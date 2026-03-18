#!/bin/bash

# Sereniq Backend Quick Start Script

echo "🚀 Starting Sereniq Backend Setup..."

# Activate virtual environment
source env/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser prompt
echo "👤 Create a superuser account:"
python manage.py createsuperuser

# Start server
echo "✅ Setup complete! Starting development server..."
python manage.py runserver
