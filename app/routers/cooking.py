from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import Recipe
from app.schemas import (
    CookingSessionStart,
    CookingSessionResponse,
    CookingMessage,
    CookingResponse
)
from app.services.claude import CookingAssistant

router = APIRouter(prefix="/cooking", tags=["cooking"])

# In-memory session storage (fine for personal project)
# Key: session_id, Value: CookingAssistant instance
active_sessions: dict[str, CookingAssistant] = {}


def _format_recipe_for_context(recipe: Recipe) -> str:
    """Format a recipe as text for Claude's context."""
    lines = [
        f"# {recipe.Name}",
        "",
        f"**Description:** {recipe.Description or 'No description'}",
        f"**Cuisine:** {recipe.Cuisine or 'Not specified'}",
        f"**Category:** {recipe.Category or 'Not specified'}",
        f"**Prep Time:** {recipe.PrepTime or '?'} minutes",
        f"**Cook Time:** {recipe.CookTime or '?'} minutes",
        f"**Servings:** {recipe.Servings or '?'}",
        "",
        "## Ingredients",
    ]

    for ri in sorted(recipe.ingredients, key=lambda x: x.OrderIndex):
        unit = ri.unit.UnitName if ri.unit else ""
        line = f"- {ri.Quantity or ''} {unit} {ri.ingredient.Name}".strip()
        lines.append(line)

    lines.extend(["", "## Steps"])

    for step in sorted(recipe.steps, key=lambda x: x.OrderIndex):
        lines.append(f"{step.OrderIndex}. {step.Description}")

    return "\n".join(lines)


@router.post("/sessions", response_model=CookingSessionResponse)
def start_cooking_session(
    request: CookingSessionStart,
    db: Session = Depends(get_db)
):
    """Start a new cooking session for a recipe."""
    recipe = db.get(Recipe, request.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Format recipe for Claude
    recipe_context = _format_recipe_for_context(recipe)

    # Create session
    session_id = str(uuid.uuid4())
    assistant = CookingAssistant(
        recipe_name=recipe.Name,
        recipe_context=recipe_context,
        total_steps=len(recipe.steps)
    )
    active_sessions[session_id] = assistant

    return CookingSessionResponse(
        session_id=session_id,
        recipe_name=recipe.Name,
        total_ingredients=len(recipe.ingredients),
        total_steps=len(recipe.steps)
    )


@router.post("/sessions/{session_id}/message", response_model=CookingResponse)
async def send_message(
    session_id: str,
    message: CookingMessage
):
    """Send a message to the cooking assistant."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not message.text:
        raise HTTPException(status_code=400, detail="Message text required")

    assistant = active_sessions[session_id]
    response_text = await assistant.chat(message.text)

    return CookingResponse(text=response_text)


@router.delete("/sessions/{session_id}", status_code=204)
def end_cooking_session(session_id: str):
    """End a cooking session."""
    if session_id in active_sessions:
        del active_sessions[session_id]


@router.get("/sessions/{session_id}")
def get_session_info(session_id: str):
    """Get info about an active session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    assistant = active_sessions[session_id]
    return {
        "session_id": session_id,
        "recipe_name": assistant.recipe_name,
        "message_count": len(assistant.messages)
    }
