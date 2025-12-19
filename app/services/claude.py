"""
Claude AI Service

This service manages conversations with Claude for cooking guidance.
It provides both synchronous and streaming interfaces to the Claude API.

Architecture:
- CookingAssistant class maintains conversation state
- System prompt includes the full recipe context
- Messages history enables contextual multi-turn conversation
- Streaming support for real-time response delivery

Why Claude for Cooking Assistance?
- Natural language understanding for varied user queries
- Contextual awareness of the full recipe
- Ability to offer substitutions and troubleshooting
- Friendly, encouraging conversational style
"""

import anthropic
from typing import AsyncGenerator

from app.config import get_settings

settings = get_settings()


class CookingAssistant:
    """
    Manages a cooking conversation with Claude.

    Each instance represents one cooking session for one recipe.
    The assistant maintains conversation history to provide
    contextual responses throughout the cooking process.

    Attributes:
        recipe_name: Name of the recipe being cooked
        recipe_context: Full recipe formatted as text
        total_steps: Number of steps in the recipe
        messages: Conversation history (user/assistant turns)
        client: Anthropic API client
    """

    SYSTEM_PROMPT = """You are a friendly, helpful cooking assistant guiding someone through a recipe.
You have the complete recipe loaded and are helping them cook it step by step.

Your personality:
- Warm and encouraging, like a friend who loves cooking
- Patient with questions and mistakes
- Concise - they're cooking with messy hands, keep responses brief
- Practical - offer substitutions, timing tips, and troubleshooting

Your capabilities:
- Guide through steps one at a time
- Answer questions about ingredients, techniques, or substitutions
- Help with timing ("how much longer?", "is it done yet?")
- Offer encouragement and tips
- Adapt if they want to skip steps or modify the recipe

Keep responses SHORT (1-3 sentences) unless they ask for detail.
When they're ready for the next step, give just that step clearly.

Here is the recipe you're helping with:

{recipe_context}
"""

    def __init__(self, recipe_name: str, recipe_context: str, total_steps: int):
        """
        Initialize a cooking assistant for a specific recipe.

        Args:
            recipe_name: The name of the recipe
            recipe_context: The full recipe formatted as markdown
            total_steps: Total number of steps in the recipe
        """
        self.recipe_name = recipe_name
        self.recipe_context = recipe_context
        self.total_steps = total_steps
        self.messages: list[dict] = []
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _get_system_prompt(self) -> str:
        """Build the system prompt with recipe context."""
        return self.SYSTEM_PROMPT.format(recipe_context=self.recipe_context)

    async def chat(self, user_message: str) -> str:
        """
        Send a message and get a complete response.

        This method:
        1. Adds the user message to history
        2. Calls Claude API with full context
        3. Adds the response to history
        4. Returns the response text

        Args:
            user_message: The user's text input

        Returns:
            Claude's response as a string
        """
        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        # Call Claude API
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=500,
            system=self._get_system_prompt(),
            messages=self.messages
        )

        # Extract response text
        assistant_message = response.content[0].text

        # Add to history for context continuity
        self.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response token by token.

        This method enables real-time display of Claude's response,
        which is better for the cooking use case where users want
        quick feedback.

        The streaming approach:
        1. Add user message to history
        2. Create a streaming request to Claude
        3. Yield each token as it arrives
        4. Accumulate the full response
        5. Add complete response to history

        Args:
            user_message: The user's text input

        Yields:
            Individual tokens/chunks of the response
        """
        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        # Create streaming request
        full_response = ""

        with self.client.messages.stream(
            model=settings.claude_model,
            max_tokens=500,
            system=self._get_system_prompt(),
            messages=self.messages
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield text

        # Add complete response to history
        self.messages.append({
            "role": "assistant",
            "content": full_response
        })
