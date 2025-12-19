# Cooking Assistant

A voice-controlled cooking assistant that guides you through recipes using natural conversation powered by Claude AI. Built with a clean MVC architecture for maintainability and scalability.

## What It Does

Cooking Assistant transforms the cooking experience by providing an AI-powered sous chef that:

- **Guides you step-by-step** through any recipe with natural conversation
- **Answers questions** like "Can I substitute butter for oil?" or "Is this done yet?"
- **Streams responses** in real-time so you get feedback immediately
- **Supports voice** input and output for hands-free cooking
- **Remembers context** throughout your cooking session

## Why We Built It This Way

### The Problem
Cooking with a recipe on your phone is frustrating:
- You can't scroll with wet hands
- You lose your place in the recipe
- You can't ask the recipe questions
- Timers and substitutions require separate apps

### The Solution
A conversational AI that knows your recipe and can:
- Read steps aloud when asked
- Answer ingredient and technique questions
- Adapt to what you have available
- Keep track of where you are

### Architecture Decision: MVC Pattern

We chose the **Model-View-Controller (MVC)** pattern for several reasons:

1. **Separation of Concerns**
   - Models handle data (what the recipe looks like)
   - Views handle presentation (how it looks to users)
   - Controllers handle logic (what happens when you click)

2. **Testability**
   - Each component can be tested independently
   - Mock the database to test controllers
   - Test views without a running server

3. **Team Scalability**
   - Frontend developers work on Views
   - Backend developers work on Controllers
   - Data engineers work on Models
   - Nobody blocks each other

4. **Future Flexibility**
   - Swap the database without changing controllers
   - Add a mobile app using the same API
   - Switch from Claude to another LLM easily

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **Backend** | Python / FastAPI | Async support, automatic OpenAPI docs, type safety |
| **Database** | Azure SQL Server | Managed service, familiar SQL, Azure integration |
| **AI** | Claude (Anthropic) | Best-in-class conversation, streaming support |
| **Voice** | Web Speech API | No additional costs, works in browser |
| **Hosting** | Azure Container Apps | Scales to zero, Docker-based, easy CI/CD |

## Project Structure (MVC)

```
cooking-assistant/
├── app/
│   ├── main.py                 # Application entry point & configuration
│   │
│   ├── models/                 # M - Data Layer
│   │   ├── __init__.py         # Exports all models
│   │   ├── entities.py         # SQLAlchemy ORM models (database tables)
│   │   └── schemas.py          # Pydantic schemas (API contracts)
│   │
│   ├── views/                  # V - Presentation Layer
│   │   ├── __init__.py
│   │   └── templates/
│   │       └── index.html      # Voice-enabled web UI
│   │
│   ├── controllers/            # C - Logic Layer
│   │   ├── __init__.py         # Exports all controllers
│   │   ├── recipes.py          # Recipe CRUD operations
│   │   └── cooking.py          # Cooking session management
│   │
│   ├── services/               # Business Logic (called by controllers)
│   │   ├── __init__.py
│   │   ├── claude.py           # Claude AI integration
│   │   └── speech.py           # Azure Speech (placeholder)
│   │
│   ├── config.py               # Environment configuration
│   └── database.py             # Database connection
│
├── static/                     # Legacy static files (backward compat)
├── infrastructure/
│   └── schema.sql              # Database DDL
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD pipeline
├── requirements.txt
├── Dockerfile
├── .env.example
└── CLAUDE.md                   # AI assistant instructions
```

### How the Layers Interact

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT                               │
│              (Browser, Mobile App, curl)                     │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP Request
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     CONTROLLERS                              │
│   recipes.py: /recipes endpoints                             │
│   cooking.py: /cooking/sessions endpoints                    │
│                                                              │
│   Responsibilities:                                          │
│   - Parse and validate requests (using Schemas)              │
│   - Call Services for business logic                         │
│   - Return formatted responses (using Schemas)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       SERVICES                               │
│   claude.py: CookingAssistant class                          │
│                                                              │
│   Responsibilities:                                          │
│   - Implement business logic                                 │
│   - Manage Claude API conversations                          │
│   - Handle streaming responses                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        MODELS                                │
│   entities.py: Recipe, Ingredient, Step (ORM)                │
│   schemas.py: RecipeCreate, CookingMessage (Pydantic)        │
│                                                              │
│   Responsibilities:                                          │
│   - Define data structures                                   │
│   - Validate incoming data                                   │
│   - Map to/from database                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATABASE                               │
│   Azure SQL Server                                           │
│   Tables: Recipes, Ingredients, Steps, etc.                  │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Recipes (CRUD)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/recipes` | List all recipes (with filtering) |
| GET | `/recipes/{id}` | Get recipe with ingredients & steps |
| POST | `/recipes` | Create a recipe |
| DELETE | `/recipes/{id}` | Delete a recipe |

### Cooking Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cooking/sessions` | Start cooking a recipe |
| POST | `/cooking/sessions/{id}/message` | Send message (standard response) |
| POST | `/cooking/sessions/{id}/stream` | Send message (streaming response) |
| GET | `/cooking/sessions/{id}` | Get session info |
| DELETE | `/cooking/sessions/{id}` | End session |

### Health & Views
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Detailed health check |
| GET | `/app` | Voice-enabled web UI |
| GET | `/docs` | OpenAPI documentation |

## Key Features Explained

### Streaming Responses

**Why streaming?**
When cooking, you want feedback immediately. Waiting 2-3 seconds for Claude to generate a complete response feels slow. Streaming shows the response as it's generated, word by word.

**How it works:**
1. Controller receives message request
2. Controller calls `CookingAssistant.chat_stream()`
3. Service creates streaming request to Claude API
4. Each token is yielded as it arrives
5. Controller wraps tokens in Server-Sent Events (SSE)
6. Frontend displays tokens in real-time

```python
# In services/claude.py
async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
    with self.client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield text  # Each token streamed immediately
```

### Voice Interface

**Why browser-based voice?**
- No additional API costs (Web Speech API is free)
- Works offline for speech recognition
- British female voice for friendly cooking guidance

**How it works:**
1. User clicks microphone button
2. Browser's SpeechRecognition API listens
3. Transcribed text sent to `/cooking/sessions/{id}/stream`
4. Response streamed back
5. Browser's SpeechSynthesis speaks the response

### Session Management

**Why in-memory sessions?**
- Cooking sessions are ephemeral (one meal)
- No need for persistence across restarts
- Simple for a personal cooking assistant
- Could upgrade to Redis for multi-instance deployments

**How it works:**
```python
# In controllers/cooking.py
active_sessions: dict[str, CookingAssistant] = {}

# Start: Create new session
session_id = str(uuid.uuid4())
active_sessions[session_id] = CookingAssistant(recipe_context)

# Message: Retrieve and use session
assistant = active_sessions[session_id]
response = await assistant.chat_stream(message.text)

# End: Clean up
del active_sessions[session_id]
```

## Database Schema

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│     Recipes     │       │  RecipeIngredients  │       │   Ingredients   │
├─────────────────┤       ├─────────────────────┤       ├─────────────────┤
│ RecipeId (PK)   │──┐    │ RecipeIngredientId  │    ┌──│ IngredientId    │
│ Name            │  │    │ RecipeId (FK)       │────┘  │ Name            │
│ Description     │  └───>│ IngredientId (FK)   │───────│                 │
│ Cuisine         │       │ UnitId (FK)         │───┐   └─────────────────┘
│ PrepTime        │       │ Quantity            │   │
│ CookTime        │       │ OrderIndex          │   │   ┌─────────────────┐
│ Servings        │       └─────────────────────┘   │   │ UnitsOfMeasure  │
└─────────────────┘                                 │   ├─────────────────┤
        │                                           └──>│ UnitId          │
        │         ┌─────────────────┐                   │ UnitName        │
        │         │      Steps      │                   └─────────────────┘
        │         ├─────────────────┤
        └────────>│ StepId          │
                  │ RecipeId (FK)   │
                  │ Description     │
                  │ OrderIndex      │
                  └─────────────────┘
```

**Why this schema?**
- **Normalized**: Ingredients and units are stored once, referenced by many recipes
- **Ordered**: Steps and ingredients maintain their order with OrderIndex
- **Cascade deletes**: Removing a recipe removes its ingredients and steps
- **Flexible quantities**: String type handles "1/2", "2-3", "a pinch"

## Local Development

### Prerequisites
- Python 3.12+
- Azure SQL database (or local SQL Server)
- Anthropic API key

### Setup

```bash
# Clone the repo
git clone https://github.com/corybeyer/cooking-assistant.git
cd cooking-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn app.main:app --reload

# Open the voice UI
open http://localhost:8000/app
```

### Test the API

```bash
# Health check
curl http://localhost:8000/

# List recipes
curl http://localhost:8000/recipes

# Start cooking session
curl -X POST http://localhost:8000/cooking/sessions \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": 1}'

# Send message (standard)
curl -X POST http://localhost:8000/cooking/sessions/{session_id}/message \
  -H "Content-Type: application/json" \
  -d '{"text": "What should I do first?"}'

# Send message (streaming)
curl -X POST http://localhost:8000/cooking/sessions/{session_id}/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "What should I do first?"}' \
  --no-buffer
```

## Docker

```bash
# Build
docker build -t cooking-assistant .

# Run
docker run -p 80:80 --env-file .env cooking-assistant
```

## Azure Deployment

### Build and Push (Azure Cloud Shell)

```bash
# Build in Azure Container Registry
az acr build \
  --registry acrcookingassistant \
  --image cooking-assistant:latest \
  https://github.com/corybeyer/cooking-assistant.git

# Update Container App
az containerapp update \
  --name ca-cooking-assistant \
  --resource-group rg-cooking-assistant \
  --image acrcookingassistant.azurecr.io/cooking-assistant:latest
```

### Required Environment Variables

Set these in Azure Container Apps:
- `DB_SERVER`: Azure SQL server hostname
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `ANTHROPIC_API_KEY`: Claude API key

## Project Status

- [x] Phase 1: Database schema design
- [x] Phase 2: FastAPI backend with Recipe CRUD
- [x] Phase 3: Claude AI integration
- [x] Phase 4: MVC architecture refactor
- [x] Phase 5: Streaming responses
- [x] Phase 6: Voice-enabled web UI
- [x] Phase 7: Azure deployment
- [ ] Phase 8: Azure Speech Services (enhanced TTS)
- [ ] Phase 9: Recipe parsing from URLs

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the MVC pattern (put code in the right layer)
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
