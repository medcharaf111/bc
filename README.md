# Backend - NATIVE OS API

Django REST API backend for the NATIVE OS adaptive learning platform.

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Virtual environment (recommended)

### Installation

1. **Create and activate virtual environment:**

**Windows:**
```bash
cd c:\Users\charaf\Desktop\jspp
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
cd ~/jspp
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

For development (includes testing and debugging tools):
```bash
pip install -r requirements-dev.txt
```

3. **Configure environment variables:**

Create a `.env` file in the `backend` directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite default)
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:8080,http://localhost:8081,http://127.0.0.1:8080
```

4. **Run migrations:**

```bash
python manage.py migrate
```

5. **Create test users (optional):**

```bash
python create_test_users.py
```

This creates:
- Teacher: `teacher@test.com` / `password123`
- Student: `student@test.com` / `password123`
- Parent: `parent@test.com` / `password123`

6. **Run development server:**

```bash
python manage.py runserver
```

API available at: `http://127.0.0.1:8000/api/`

## 📦 Dependencies

### Core Framework
- **Django 4.2+** - Web framework
- **Django REST Framework 3.14+** - API framework
- **djangorestframework-simplejwt 5.3+** - JWT authentication

### Security & CORS
- **django-cors-headers 4.3+** - Cross-Origin Resource Sharing

### AI Integration
- **google-generativeai 0.8+** - Gemini AI for content generation and grading

### Utilities
- **Pillow 10.0+** - Image processing
- **pytz 2023.3+** - Timezone support
- **daphne 4.0+** - ASGI server

## 🗂️ Project Structure

```
backend/
├── accounts/           # User authentication and management
├── core/              # Core learning functionality
│   ├── models.py      # Lesson, MCQTest, QATest models
│   ├── views.py       # API endpoints
│   ├── serializers.py # Data serialization
│   └── ai_service.py  # Gemini AI integration
├── native_os/         # Project settings
│   ├── settings.py    # Configuration
│   ├── urls.py        # URL routing
│   └── wsgi.py        # WSGI config
├── manage.py          # Django management script
├── requirements.txt   # Production dependencies
└── requirements-dev.txt # Development dependencies
```

## 🔌 API Endpoints

### Authentication
- `POST /api/register/` - User registration
- `POST /api/login/` - User login (returns JWT tokens)
- `POST /api/token/refresh/` - Refresh JWT token

### Lessons
- `GET /api/lessons/` - List all lessons
- `POST /api/lessons/` - Create lesson (teacher only)
- `GET /api/lessons/{id}/` - Get lesson detail
- `PUT /api/lessons/{id}/` - Update lesson
- `DELETE /api/lessons/{id}/` - Delete lesson

### MCQ Tests
- `GET /api/mcq-tests/` - List MCQ tests
- `POST /api/mcq-tests/generate-mcq/` - Generate MCQ test (teacher)
- `POST /api/mcq-tests/{id}/approve/` - Approve test (teacher)
- `POST /api/mcq-tests/{id}/reject/` - Reject test (teacher)
- `GET /api/mcq-tests/pending/` - Get pending tests (teacher)
- `POST /api/mcq-submissions/submit/` - Submit MCQ test (student)

### Q&A Tests
- `GET /api/qa-tests/` - List Q&A tests
- `POST /api/qa-tests/generate-qa-test/` - Generate Q&A test (teacher)
- `POST /api/qa-tests/{id}/approve/` - Approve test (teacher)
- `POST /api/qa-tests/{id}/reject/` - Reject test (teacher)
- `GET /api/qa-tests/pending/` - Get pending tests (teacher)
- `POST /api/qa-submissions/submit/` - Submit Q&A test (student)
- `POST /api/qa-submissions/{id}/finalize/` - Finalize grade (teacher)
- `GET /api/qa-submissions/pending_review/` - Get submissions to review

## 🧪 Testing

Run tests:
```bash
pytest
```

With coverage:
```bash
coverage run -m pytest
coverage report
```

## 🔧 Development Tools

### Django Debug Toolbar
```bash
# Already included in requirements-dev.txt
# Access at http://localhost:8000/__debug__/
```

### Django Shell
```bash
python manage.py shell
```

### Database Shell
```bash
python manage.py dbshell
```

### Create Superuser
```bash
python manage.py createsuperuser
```

## 📝 Common Commands

```bash
# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run on different port
python manage.py runserver 8001

# Run tests
pytest

# Format code
black .

# Lint code
flake8
```

## 🔐 Security Notes

1. **Never commit `.env` file** - Contains sensitive data
2. **Use strong SECRET_KEY** in production
3. **Set DEBUG=False** in production
4. **Configure ALLOWED_HOSTS** properly
5. **Use HTTPS** in production
6. **Keep dependencies updated**: `pip install --upgrade -r requirements.txt`

## 🚀 Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn native_os.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Using Daphne (ASGI)

```bash
daphne -b 0.0.0.0 -p 8000 native_os.asgi:application
```

### Environment Setup

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=generate-a-strong-secret-key
DATABASE_URL=postgresql://user:password@db-host:5432/dbname
```

## 🐛 Troubleshooting

### Issue: "No module named 'django'"
```bash
# Make sure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Database errors
```bash
# Reset database (WARNING: deletes all data)
python manage.py flush
python manage.py migrate
```

### Issue: CORS errors
```bash
# Check CORS_ALLOWED_ORIGINS in settings.py
# Make sure frontend URL is included
```

### Issue: AI/Gemini errors
```bash
# Verify GEMINI_API_KEY is set in .env
# Check API key is valid at https://makersuite.google.com/app/apikey
# Ensure google-generativeai is installed
pip install --upgrade google-generativeai
```

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Google Gemini API](https://ai.google.dev/docs)
- [JWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Run tests and linting
5. Submit pull request

## 📄 License

[Your License Here]
