# Cooking Assistant

A voice-controlled cooking assistant that guides you through recipes using natural conversation powered by Claude.

## Features

- **Natural conversation**: Ask questions like "what if I don't have celery?" or "is this done yet?"
- **Step-by-step guidance**: Claude walks you through each recipe step
- **Hands-free cooking**: Voice input/output (coming soon)

## Tech Stack

- **Backend**: Python / FastAPI
- **Database**: Azure SQL
- **AI**: Claude (Anthropic API)
- **Voice**: Azure Speech Services (Phase 4)
- **Hosting**: Azure Container Apps

## Project Structure

```
cooking-assistant/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings & environment
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── recipes.py       # Recipe CRUD endpoints
│   │   └── cooking.py       # Cooking session endpoints
│   └── services/
│       ├── claude.py        # Claude API integration
│       └── speech.py        # Azure Speech (placeholder)
├── infrastructure/
│   └── schema.sql           # Database DDL
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API Endpoints

### Recipes (CRUD)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/recipes` | List all recipes |
| GET | `/recipes/{id}` | Get recipe with ingredients & steps |
| POST | `/recipes` | Create a recipe |
| DELETE | `/recipes/{id}` | Delete a recipe |

### Cooking Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cooking/sessions` | Start cooking a recipe |
| POST | `/cooking/sessions/{id}/message` | Send message to assistant |
| GET | `/cooking/sessions/{id}` | Get session info |
| DELETE | `/cooking/sessions/{id}` | End session |

## Local Development

### Prerequisites
- Python 3.12+
- Azure SQL database (or SQL Server)
- Anthropic API key

### Setup

```bash
# Clone the repo
git clone https://github.com/corybeyer/cooking-assistant.git
cd cooking-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn app.main:app --reload
```

### Test the API

```bash
# Health check
curl http://localhost:8000/

# List recipes
curl http://localhost:8000/recipes

# Create a recipe
curl -X POST http://localhost:8000/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Recipe",
    "ingredients": [{"name": "salt", "quantity": "1", "unit": "tsp"}],
    "steps": [{"description": "Add salt to water"}]
  }'
```

## Docker

```bash
# Build
docker build -t cooking-assistant .

# Run
docker run -p 80:80 --env-file .env cooking-assistant
```

## Roadmap

- [x] Phase 1: Database schema
- [x] Phase 2: FastAPI + Recipe CRUD
- [x] Phase 3: Claude integration
- [ ] Phase 4: Azure Speech (voice)
- [ ] Phase 5: Web frontend
- [ ] Phase 6: Deploy to Azure
