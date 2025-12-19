# CLAUDE.md

This file provides context for Claude Code to understand and work with this project.

## Project Overview

**Cooking Assistant** is a voice-controlled cooking application that guides users through recipes using natural conversation powered by Claude AI. Users can ask questions like "what's next?", "can I substitute X?", or "is this done yet?" while cooking.

## Tech Stack

- **Backend**: Python 3.12 / FastAPI
- **Database**: Azure SQL Server (SQL Server compatible)
- **AI**: Claude API (Anthropic) for conversational guidance
- **Voice** (planned): Azure Speech Services for STT/TTS
- **Hosting**: Azure Container Apps
- **CI/CD**: GitHub Actions (planned)

## Project Structure

```
cooking-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic settings (env vars)
│   ├── database.py          # SQLAlchemy engine and session
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── recipes.py       # /recipes CRUD endpoints
│   │   └── cooking.py       # /cooking session endpoints
│   └── services/
│       ├── __init__.py
│       ├── claude.py        # Claude API integration
│       └── speech.py        # Azure Speech (placeholder)
├── infrastructure/
│   └── schema.sql           # Database DDL (tables, indexes, stored procs)
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## Database Schema

The database has 5 main tables:

| Table | Purpose |
|-------|---------|
| `Recipes` | Recipe metadata (name, description, times, servings) |
| `Ingredients` | Normalized ingredient names (deduplicated) |
| `UnitsOfMeasure` | Normalized units (deduplicated) |
| `RecipeIngredients` | Links recipes to ingredients with quantities |
| `Steps` | Recipe preparation steps with order |

Key relationships:
- `Recipe` → has many `RecipeIngredients` → each links to one `Ingredient` and optionally one `UnitOfMeasure`
- `Recipe` → has many `Steps` (ordered by `OrderIndex`)
- Foreign keys use `ON DELETE CASCADE` for recipes

The full DDL is in `infrastructure/schema.sql`.

## API Endpoints

### Recipe CRUD (`/recipes`)
- `GET /recipes` - List recipes (optional filters: cuisine, category)
- `GET /recipes/{id}` - Get recipe with ingredients and steps
- `POST /recipes` - Create recipe with ingredients and steps
- `DELETE /recipes/{id}` - Delete recipe (cascades)

### Cooking Sessions (`/cooking`)
- `POST /cooking/sessions` - Start cooking session for a recipe
- `POST /cooking/sessions/{id}/message` - Send message to Claude assistant
- `GET /cooking/sessions/{id}` - Get session info
- `DELETE /cooking/sessions/{id}` - End session

## Key Patterns

### Configuration
Settings are loaded from environment variables via Pydantic:
```python
from app.config import get_settings
settings = get_settings()
```

Required env vars: `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `ANTHROPIC_API_KEY`

### Database Sessions
Use FastAPI dependency injection:
```python
from app.database import get_db

@router.get("/recipes")
def list_recipes(db: Session = Depends(get_db)):
    ...
```

### Pydantic Schemas
- Input schemas: `RecipeCreate`, `IngredientInput`, `StepInput`, `CookingMessage`
- Output schemas: `RecipeSummary`, `RecipeDetail`, `CookingResponse`
- All schemas in `app/schemas.py`

### Cooking Sessions
Sessions are stored in memory (dict) since they're ephemeral:
```python
# In app/routers/cooking.py
active_sessions: dict[str, CookingAssistant] = {}
```

Each session holds:
- Recipe context (formatted as text)
- Conversation history (messages list)
- Claude client instance

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Run with Docker
docker build -t cooking-assistant .
docker run -p 80:80 --env-file .env cooking-assistant
```

## Code Conventions

- **Naming**: SQLAlchemy models use PascalCase column names (matching SQL Server). Pydantic schemas use snake_case.
- **Async**: The Claude service uses `async def` but calls the sync Anthropic client. Can be refactored to use async client later.
- **Error handling**: Use `HTTPException` from FastAPI for API errors.
- **Type hints**: All functions should have type hints.

## Current Status

- [x] Database schema designed
- [x] FastAPI project structure
- [x] Recipe CRUD endpoints
- [x] Claude integration (CookingAssistant class)
- [ ] Azure Speech integration
- [ ] Web frontend
- [ ] Docker deployment to Azure
- [ ] GitHub Actions CI/CD

## Future Work

1. **Voice integration**: Implement `app/services/speech.py` with Azure Speech SDK
2. **Frontend**: Simple web UI with push-to-talk button
3. **Recipe parsing**: Endpoint to parse raw recipe text into structured JSON (Claude-powered)
4. **Session persistence**: Optionally store sessions in Redis for multi-instance deployments
