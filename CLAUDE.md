# CLAUDE.md

This file provides context for Claude Code to understand and work with this project.

## Project Overview

**Cooking Assistant** is a voice-controlled cooking application that guides users through recipes using natural conversation powered by Claude AI. Users can ask questions like "what's next?", "can I substitute X?", or "is this done yet?" while cooking.

## Architecture

This is a **Streamlit application** with a simple, direct architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    streamlit_app.py                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  UI Layer (Streamlit)                               │   │
│  │  - Recipe selection                                 │   │
│  │  - Voice input (speech_recognition)                 │   │
│  │  - Chat interface                                   │   │
│  │  - Text-to-speech output (gTTS)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│           ┌──────────────┼──────────────┐                  │
│           ▼              ▼              ▼                  │
│    ┌───────────┐  ┌───────────┐  ┌───────────────┐        │
│    │ SQLAlchemy│  │ Anthropic │  │ Speech/TTS    │        │
│    │ (Database)│  │ (Claude)  │  │ (Voice I/O)   │        │
│    └───────────┘  └───────────┘  └───────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Frontend/Backend**: Python 3.12 / Streamlit
- **Database**: Azure SQL Server via SQLAlchemy
- **AI**: Claude API (Anthropic)
- **Voice Input**: speech_recognition (Google Speech Recognition - free)
- **Voice Output**: gTTS (Google Text-to-Speech)
- **Hosting**: Azure Container Apps
- **CI/CD**: GitHub Actions

## Project Structure

```
cooking-assistant/
├── streamlit_app.py          # Main application (UI + logic)
├── app/
│   ├── __init__.py
│   ├── config.py             # Pydantic settings
│   ├── database.py           # SQLAlchemy connection
│   └── models/
│       ├── __init__.py       # Exports all models
│       └── entities.py       # SQLAlchemy ORM models
│
├── infrastructure/
│   └── schema.sql            # Database DDL
├── .github/workflows/
│   └── deploy.yml            # CI/CD pipeline
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `Recipes` | Recipe metadata (name, description, times, servings) |
| `Ingredients` | Normalized ingredient names |
| `UnitsOfMeasure` | Normalized units |
| `RecipeIngredients` | Links recipes to ingredients with quantities |
| `Steps` | Recipe preparation steps with order |

Key relationships:
- `Recipe` → has many `RecipeIngredients` → each links to `Ingredient` and optional `UnitOfMeasure`
- `Recipe` → has many `Steps` (ordered by `OrderIndex`)
- Foreign keys use `ON DELETE CASCADE`

## Key Patterns

### Configuration
```python
from app.config import get_settings
settings = get_settings()
```

Required env vars: `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `ANTHROPIC_API_KEY`

### Database Access
```python
from app.database import SessionLocal
from app.models import Recipe

db = SessionLocal()
recipes = db.query(Recipe).all()
db.close()
```

### Streamlit Session State
```python
if "messages" not in st.session_state:
    st.session_state.messages = []
```

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run streamlit_app.py

# Run with Docker
docker build -t cooking-assistant .
docker run -p 80:80 --env-file .env cooking-assistant
```

## Application Flow

1. **Recipe Selection**: User picks a recipe from the database
2. **Prep Phase**: Claude guides through gathering ingredients
3. **Cooking Phase**: Step-by-step guidance with voice I/O
4. **Conversation**: User can ask questions anytime ("what's next?", "can I substitute?")

## Code Conventions

- **Type hints**: All functions should have type hints
- **Streamlit caching**: Use `@st.cache_data` for database queries
- **Session state**: Store conversation history in `st.session_state`

## Current Status

- [x] Database schema designed
- [x] Streamlit app with voice I/O
- [x] Claude integration for cooking guidance
- [x] Docker deployment to Azure
- [x] GitHub Actions CI/CD

## Future Work

1. **Recipe parsing**: Add recipes from URLs
2. **Session persistence**: Redis for multi-instance deployments
3. **Mobile app**: React Native app using a REST API (would require adding FastAPI back)
