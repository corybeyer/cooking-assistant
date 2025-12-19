"""
Cooking Controller

Manages interactive cooking sessions powered by Claude AI.
Provides both standard request/response and streaming endpoints.

Session Lifecycle:
1. User starts a session with a recipe_id
2. Recipe is loaded and formatted as context for Claude
3. User sends messages (text or voice-transcribed)
4. Claude responds with cooking guidance
5. User ends the session when done

Streaming:
The /stream endpoint uses Server-Sent Events (SSE) to deliver
Claude's response token-by-token, providing a more responsive
experience during cooking when quick feedback matters.

Why In-Memory Sessions?
- Sessions are ephemeral (one cooking session)
- No need for persistence across restarts
- Simple for a personal cooking assistant
- Could be upgraded to Redis for multi-instance deployments
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import uuid
import json

from app.database import get_db
from app.models import (
    Recipe,
    CookingSessionStart,
    CookingSessionResponse,
    CookingMessage,
    CookingResponse
)
from app.services.claude import CookingAssistant

router = APIRouter(prefix="/cooking", tags=["cooking"])

# In-memory session storage
# Key: session_id, Value: CookingAssistant instance
active_sessions: dict[str, CookingAssistant] = {}


def _format_recipe_for_context(recipe: Recipe) -> str:
    """
    Format a recipe as markdown text for Claude's context.

    This formatting is crucial for Claude's understanding:
    - Clear structure with headers
    - All relevant metadata included
    - Ingredients listed with quantities
    - Steps numbered for easy reference

    The formatted text becomes part of Claude's system prompt,
    giving it complete knowledge of the recipe being cooked.
    """
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
    """
    Start a new cooking session for a recipe.

    This creates a CookingAssistant instance that:
    - Has the complete recipe in its context
    - Maintains conversation history
    - Can be used for the duration of cooking

    Returns session metadata including the session_id needed
    for subsequent message and stream requests.
    """
    recipe = db.get(Recipe, request.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Format recipe for Claude's context
    recipe_context = _format_recipe_for_context(recipe)

    # Create session with unique ID
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
    """
    Send a message and get a complete response.

    Use this endpoint for:
    - Simple text exchanges
    - When streaming is not needed
    - Testing and debugging

    For a better user experience during cooking, consider
    using the /stream endpoint instead.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not message.text:
        raise HTTPException(status_code=400, detail="Message text required")

    assistant = active_sessions[session_id]
    response_text = await assistant.chat(message.text)

    return CookingResponse(text=response_text)


@router.post("/sessions/{session_id}/stream")
async def stream_message(
    session_id: str,
    message: CookingMessage
):
    """
    Send a message and stream the response via Server-Sent Events.

    SSE Format:
    - event: token (for each piece of text)
    - event: done (when complete)
    - event: error (if something goes wrong)

    Benefits of streaming:
    - Faster perceived response time
    - User sees response building in real-time
    - Better for hands-free cooking scenarios
    - Can be interrupted if needed

    The frontend should use EventSource or fetch with ReadableStream
    to consume this endpoint.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not message.text:
        raise HTTPException(status_code=400, detail="Message text required")

    assistant = active_sessions[session_id]

    async def generate():
        """Generator that yields SSE-formatted events."""
        try:
            async for token in assistant.chat_stream(message.text):
                # SSE format: data: <content>\n\n
                data = json.dumps({"token": token})
                yield f"data: {data}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.delete("/sessions/{session_id}", status_code=204)
def end_cooking_session(session_id: str):
    """
    End a cooking session and clean up resources.

    Call this when:
    - User is done cooking
    - User wants to switch recipes
    - User closes the app

    Cleans up the in-memory session to free resources.
    """
    if session_id in active_sessions:
        del active_sessions[session_id]


@router.get("/sessions/{session_id}")
def get_session_info(session_id: str):
    """
    Get information about an active session.

    Useful for:
    - Checking if a session is still valid
    - Getting session statistics
    - Debugging
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    assistant = active_sessions[session_id]
    return {
        "session_id": session_id,
        "recipe_name": assistant.recipe_name,
        "message_count": len(assistant.messages)
    }
