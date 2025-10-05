# Stash - Video Content Organizer

Transform saved YouTube videos into organized, AI-powered summaries. Never lose track of valuable video content again.

## Overview

Stash solves the common problem of saving videos for later but never revisiting them. The application automatically extracts transcripts from YouTube videos and generates intelligent, structured summaries using AI, making your saved content instantly accessible.

## Features

- **Automatic Transcript Extraction**: Fetches video transcripts directly from YouTube
- **AI-Powered Summaries**: Generates adaptive summaries using Groq's Llama 3.3 70B model
  - Recipe videos → ingredients + step-by-step instructions
  - Travel videos → itineraries with places and tips
  - Educational content → key points and takeaways
- **CRUD Operations**: Full Create, Read, Update, Delete functionality
- **Persistent Storage**: SQLite database for reliable data persistence
- **Modern UI**: Clean, responsive interface with Tailwind CSS
- **RESTful API**: Well-documented API endpoints with automatic OpenAPI docs

## Tech Stack

**Backend:**
- Python 3.9+
- FastAPI (web framework)
- SQLite (database)
- Groq API (AI summarization)
- youtube-transcript-api (transcript extraction)

**Frontend:**
- HTML5
- Tailwind CSS
- Vanilla JavaScript

**Testing:**
- Pytest
- Coverage.py (90%+ code coverage)

## Installation

### Prerequisites

- Python 3.9 or higher
- Git
- Groq API key ([Get one here](https://console.groq.com))

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/dianacord/stash.git
   cd stash
   ```

2. **Create and activate virtual environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate it
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Create .env file from example
   cp .env.example .env
   
   # Edit .env and add your Groq API key
   # GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Initialize database**
   ```bash
   # Database will be created automatically on first run
   # No manual setup needed
   ```

## Running the Application

### Start the Backend Server

```bash
# From project root directory
uvicorn backend.main:app --reload --port 8080
```

The server will start at `http://localhost:8080`

### Access the Application

- **Web Interface**: http://localhost:8080 (open `frontend/index.html` in browser)
- **API Documentation**: http://localhost:8080/docs (interactive Swagger UI)
- **Alternative API Docs**: http://localhost:8080/redoc
- **Health Check**: http://localhost:8080/api/health

### Using the Web Interface

1. Open `frontend/index.html` in your web browser
2. Paste any YouTube URL in the search box
3. Click "Save & Summarize"
4. Wait for AI processing (usually 5-10 seconds)
5. View your organized summaries below

## Running Tests

### Run All Tests

```bash
# Run tests with verbose output
PYTHONPATH=. pytest tests/ -v
```

### Check Code Coverage

```bash
# Run tests with coverage report
PYTHONPATH=. pytest tests/ -v --cov=backend --cov-report=html --cov-report=term

# Open HTML coverage report
open htmlcov/index.html  # macOS
# or
start htmlcov/index.html  # Windows
# or
xdg-open htmlcov/index.html  # Linux
```

**Current Coverage**: 90%

### Run Specific Tests

```bash
# Test specific module
PYTHONPATH=. pytest tests/test_api.py -v

# Test specific function
PYTHONPATH=. pytest tests/test_api.py::test_save_video_success -v
```

## API Endpoints

### Core Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/videos` | Save new video with AI summary |
| `GET` | `/api/videos` | Get all saved videos |
| `GET` | `/api/videos/{video_id}` | Get specific video by ID |
| `PUT` | `/api/videos/{id}` | Update video summary or metadata |
| `DELETE` | `/api/videos/{id}` | Delete video entry |
| `GET` | `/api/health` | Health check endpoint |

### Example API Usage

**Save a video:**
```bash
curl -X POST http://localhost:8080/api/videos \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

**Get all videos:**
```bash
curl http://localhost:8080/api/videos
```

**Update a video:**
```bash
curl -X PUT http://localhost:8080/api/videos/1 \
  -H "Content-Type: application/json" \
  -d '{"ai_summary": "Updated summary text"}'
```

**Delete a video:**
```bash
curl -X DELETE http://localhost:8080/api/videos/1
```

## Project Structure

```
stash/
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application + routes
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py        # User authentication service
│       ├── database.py            # SQLite database service
│       ├── groq_summarizer.py     # AI summarization service
│       └── youtube_fetcher.py     # YouTube transcript extraction
├── frontend/
│   └── index.html                 # Web interface (HTML + JS + CSS)
├── tests/
│   ├── conftest.py                # Pytest fixtures and configuration
│   ├── test_api.py                # API endpoint tests
│   ├── test_auth_service.py       # Authentication tests
│   ├── test_database.py           # Database operation tests
│   ├── test_groq_summarizer.py    # AI service tests
│   └── test_youtube_fetcher.py    # YouTube service tests
├── docs/                          # Documentation and diagrams
├── .env.example                   # Environment variables template
├── .coveragerc                    # Coverage configuration
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── stash.db                       # SQLite database (created on first run)
└── README.md                      # This file
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Groq API (Required)
GROQ_API_KEY=your_groq_api_key_here

```

### Database

The application uses SQLite with the following schema:

```sql
saved_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    video_id TEXT NOT NULL UNIQUE,
    platform TEXT DEFAULT 'youtube',
    title TEXT,
    raw_transcript TEXT,
    ai_summary TEXT,
    language TEXT,
    is_generated BOOLEAN,
    segments_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Database file: `stash.db` (created automatically)

## Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'backend'"**
```bash
# Make sure you're using PYTHONPATH
PYTHONPATH=. pytest tests/ -v
# or run from project root
```

**"GROQ_API_KEY not found"**
```bash
# Check your .env file exists and has the key
cat .env
# Make sure you've activated the virtual environment
```

**"Video transcript not available"**
- Not all YouTube videos have transcripts/captions
- Try a different video with closed captions enabled
- Check if the video is publicly accessible

**Tests failing with database errors**
```bash
# Clean up test databases
rm test_*.db
# Run tests again
PYTHONPATH=. pytest tests/ -v
```

## Future Enhancements

- Multi-platform support (TikTok, Twitter, LinkedIn)
- Tag-based content organization
- Full-text search across transcripts and summaries
- Export functionality (PDF, Markdown)
- Browser extension for one-click saving
- Real-time collaboration features

## Development

### Code Quality

- Type hints used throughout codebase
- Comprehensive docstrings
- 90%+ test coverage
- Clean architecture with separation of concerns
- RESTful API design principles

### Design Patterns

- Repository Pattern (database abstraction)
- Service Layer Pattern (business logic)
- Factory Pattern (service instantiation)
- MVC architecture (separation of concerns)

## License

This project is part of an academic assignment for the Software Development and DevOps course.

## Author

**Diana Cordovez**
- Course: Software Development and DevOps
- Date: September/October 2025
- Assignment: Individual Assignment 1

## Acknowledgments

- FastAPI for excellent documentation and framework
- Groq for AI API access
- youtube-transcript-api for transcript extraction
- Tailwind CSS for styling utilities

---

**Note**: This application is designed for educational purposes as part of a software development course. It demonstrates CRUD operations, API integration, database design, and modern web development practices.