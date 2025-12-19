# CLAUDE.md

This file provides context for Claude Code to understand and work with this project.

## Project Overview

**Cooking Assistant** is a voice-controlled cooking application that guides users through recipes using natural conversation powered by Claude AI. Users can ask questions like "what's next?", "can I substitute X?", or "is this done yet?" while cooking.

## Architecture: MVC Pattern

This project follows the **Model-View-Controller (MVC)** pattern:

- **Models** (`app/models/`): Data structures and validation
- **Views** (`app/views/`): User interface templates
- **Controllers** (`app/controllers/`): Request handling and routing
- **Services** (`app/services/`): Business logic layer

## Tech Stack

- **Backend**: Python 3.12 / FastAPI
- **Database**: Azure SQL Server
- **AI**: Claude API (Anthropic) with streaming support
- **Voice**: Web Speech API (browser-based)
- **Hosting**: Azure Container Apps
- **CI/CD**: GitHub Actions

## Project Structure

```
cooking-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Pydantic settings
│   ├── database.py             # SQLAlchemy connection
│   │
│   ├── models/                 # M - Data Layer
│   │   ├── __init__.py         # Exports all models
│   │   ├── entities.py         # SQLAlchemy ORM models
│   │   └── schemas.py          # Pydantic schemas (DTOs)
│   │
│   ├── views/                  # V - Presentation Layer
│   │   ├── __init__.py
│   │   └── templates/
│   │       └── index.html      # Voice-enabled web UI
│   │
│   ├── controllers/            # C - Logic Layer
│   │   ├── __init__.py
│   │   ├── recipes.py          # /recipes CRUD
│   │   └── cooking.py          # /cooking sessions
│   │
│   └── services/               # Business Logic
│       ├── __init__.py
│       ├── claude.py           # Claude AI with streaming
│       └── speech.py           # Azure Speech (placeholder)
│
├── static/                     # Legacy static files
├── infrastructure/
│   └── schema.sql              # Database DDL
├── .github/workflows/
│   └── deploy.yml              # CI/CD pipeline
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

## API Endpoints

### Recipe CRUD (`/recipes`)
- `GET /recipes` - List recipes (with filtering)
- `GET /recipes/{id}` - Get recipe with ingredients and steps
- `POST /recipes` - Create recipe
- `DELETE /recipes/{id}` - Delete recipe

### Cooking Sessions (`/cooking`)
- `POST /cooking/sessions` - Start session for a recipe
- `POST /cooking/sessions/{id}/message` - Send message (standard)
- `POST /cooking/sessions/{id}/stream` - Send message (streaming via SSE)
- `GET /cooking/sessions/{id}` - Get session info
- `DELETE /cooking/sessions/{id}` - End session

### Views
- `GET /app` - Voice-enabled web UI
- `GET /docs` - OpenAPI documentation

## Key Patterns

### Importing Models
```python
# Import from the models package
from app.models import Recipe, RecipeCreate, CookingMessage
```

### Importing Controllers
```python
# In main.py
from app.controllers import recipes_router, cooking_router
app.include_router(recipes_router)
app.include_router(cooking_router)
```

### Configuration
```python
from app.config import get_settings
settings = get_settings()
```

Required env vars: `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `ANTHROPIC_API_KEY`

### Database Sessions
```python
from app.database import get_db

@router.get("/recipes")
def list_recipes(db: Session = Depends(get_db)):
    ...
```

### Streaming Responses
```python
# In services/claude.py
async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
    with self.client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield text

# In controllers/cooking.py
@router.post("/sessions/{session_id}/stream")
async def stream_message(session_id: str, message: CookingMessage):
    async def generate():
        async for token in assistant.chat_stream(message.text):
            yield f"data: {json.dumps({'token': token})}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Cooking Sessions
Sessions are stored in memory (ephemeral):
```python
# In controllers/cooking.py
active_sessions: dict[str, CookingAssistant] = {}
```

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Open voice UI
open http://localhost:8000/app

# Run with Docker
docker build -t cooking-assistant .
docker run -p 80:80 --env-file .env cooking-assistant
```

## Code Conventions

- **MVC Organization**: Put code in the appropriate layer
  - Data structures → `models/`
  - Request handlers → `controllers/`
  - Business logic → `services/`
  - HTML templates → `views/templates/`

- **Naming**:
  - SQLAlchemy models use PascalCase columns (matching SQL Server)
  - Pydantic schemas use snake_case
  - Controllers export `router` variable

- **Type hints**: All functions should have type hints

- **Error handling**: Use `HTTPException` from FastAPI

## Current Status

- [x] Database schema designed
- [x] MVC architecture implemented
- [x] Recipe CRUD endpoints
- [x] Claude integration with streaming
- [x] Voice-enabled web UI
- [x] Docker deployment to Azure
- [ ] Azure Speech Services (enhanced TTS)
- [ ] Recipe parsing from URLs
- [ ] GitHub Actions CI/CD secrets

## Future Work

1. **Azure Speech**: Replace Web Speech API with Azure for better voice quality
2. **Recipe parsing**: Endpoint to parse recipe URLs into structured JSON
3. **Session persistence**: Redis for multi-instance deployments
4. **Mobile app**: React Native app using the same API
