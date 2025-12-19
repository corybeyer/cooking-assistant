import anthropic
from app.config import get_settings

settings = get_settings()


class CookingAssistant:
    """Manages a cooking conversation with Claude."""

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
        self.recipe_name = recipe_name
        self.recipe_context = recipe_context
        self.total_steps = total_steps
        self.messages: list[dict] = []
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def chat(self, user_message: str) -> str:
        """Send a message and get a response from Claude."""

        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        # Build system prompt with recipe
        system = self.SYSTEM_PROMPT.format(recipe_context=self.recipe_context)

        # Call Claude API
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=500,
            system=system,
            messages=self.messages
        )

        # Extract response text
        assistant_message = response.content[0].text

        # Add to history
        self.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message
