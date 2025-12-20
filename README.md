# Cooking Assistant

A voice-controlled cooking assistant that guides you through recipes using natural conversation powered by Claude AI.

## What It Does

Cooking Assistant provides an AI-powered sous chef that:

- **Guides you step-by-step** through any recipe with natural conversation
- **Answers questions** like "Can I substitute butter for oil?" or "Is this done yet?"
- **Supports voice input and output** for hands-free cooking
- **Remembers context** throughout your cooking session

### The Problem

Cooking with a recipe on your phone is frustrating—you can't scroll with wet hands, you lose your place, and you can't ask questions.

### The Solution

A conversational AI that knows your recipe and can read steps aloud, answer questions, suggest substitutions, and keep track of where you are.

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **Framework** | Streamlit | Fast prototyping, built-in UI components, session state |
| **Database** | Azure SQL Server + SQLAlchemy | Managed service, ORM for type safety |
| **AI** | Claude API (Anthropic) | Best-in-class conversation |
| **Voice Input** | SpeechRecognition (Google) | Free, no API key needed |
| **Voice Output** | gTTS (Google Text-to-Speech) | Free, British accent for friendly guidance |
| **Hosting** | Azure Container Apps | Scales to zero, Docker-based |
| **Auth** | Azure Easy Auth (Entra ID) | Managed authentication layer |
| **IaC** | Azure Bicep | Reproducible, modular infrastructure |

## Project Structure

```
cooking-assistant/
├── streamlit_app.py          # Main application (UI + all logic)
├── app/
│   ├── config.py             # Pydantic settings management
│   ├── database.py           # SQLAlchemy connection
│   └── models/
│       ├── __init__.py       # Model exports
│       └── entities.py       # ORM models (Recipe, Ingredient, Step, etc.)
├── infrastructure/
│   ├── schema.sql            # Database DDL + stored procedures
│   └── bicep/                # Infrastructure as Code (Azure)
│       ├── main.bicep        # Main orchestration template
│       ├── modules/          # Modular resource definitions
│       └── parameters/       # Environment-specific params
├── .github/workflows/
│   └── deploy.yml            # CI/CD pipeline
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Application Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    streamlit_app.py                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  UI Layer (Streamlit)                               │   │
│  │  - Recipe selection dropdown                        │   │
│  │  - Voice input (st.audio_input)                     │   │
│  │  - Chat interface                                   │   │
│  │  - Audio playback (st.audio)                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│           ┌──────────────┼──────────────┐                  │
│           ▼              ▼              ▼                  │
│    ┌───────────┐  ┌───────────┐  ┌───────────────┐        │
│    │ SQLAlchemy│  │ Anthropic │  │ gTTS/SpeechRec│        │
│    │ (Database)│  │ (Claude)  │  │ (Voice I/O)   │        │
│    └───────────┘  └───────────┘  └───────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

**Cooking Phases:**
1. **Recipe Selection** — User picks a recipe from the database
2. **Prep Phase** — Claude helps gather and prepare ingredients
3. **Cooking Phase** — Step-by-step guidance triggered by "ready" or "let's start"
4. **Conversation** — User asks questions anytime via voice or text

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

- **Normalized** — Ingredients and units stored once, referenced by many recipes
- **Ordered** — Steps and ingredients maintain order with `OrderIndex`
- **Cascade deletes** — Removing a recipe removes its ingredients and steps
- **Flexible quantities** — String type handles "1/2", "2-3", "a pinch"

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

# Run the app
streamlit run streamlit_app.py
```

Open http://localhost:8501 in your browser.

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `DB_SERVER` | Azure SQL server hostname |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `ANTHROPIC_API_KEY` | Claude API key |

## Docker

```bash
# Build
docker build -t cooking-assistant .

# Run
docker run -p 80:80 --env-file .env cooking-assistant
```

## Azure Deployment

### Option 1: Infrastructure as Code (Recommended)

Deploy the complete infrastructure using Azure Bicep:

```bash
# Create resource group
az group create --name rg-cooking-assistant-dev --location eastus

# Deploy all resources
az deployment group create \
  --resource-group rg-cooking-assistant-dev \
  --template-file infrastructure/bicep/main.bicep \
  --parameters infrastructure/bicep/parameters/dev.bicepparam \
  --parameters sqlAdminPassword='<password>' \
  --parameters anthropicApiKey='<api-key>'
```

This creates: Container Registry, SQL Server + Database, Key Vault, Container Apps Environment, Container App with Managed Identity, and Log Analytics.

See [infrastructure/bicep/README.md](infrastructure/bicep/README.md) for full documentation.

### Option 2: Manual Deployment

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

## Security Features

- **Authentication** — Azure Container Apps Easy Auth (Entra ID)
- **Rate Limiting** — 30 requests per 60 seconds to prevent API abuse
- **Error Handling** — Server-side logging only, errors not exposed to users
- **Temp File Cleanup** — Audio files cleaned up to prevent disk exhaustion

## Project Status

- [x] Database schema design
- [x] Streamlit app with voice I/O
- [x] Claude AI integration
- [x] Docker deployment to Azure
- [x] GitHub Actions CI/CD
- [x] Rate limiting and auth
- [x] Infrastructure as Code (Bicep)
- [ ] Recipe parsing from URLs
- [ ] Session persistence (Redis for multi-instance)

## License

MIT License - see LICENSE file for details.
