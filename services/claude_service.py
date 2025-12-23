"""
Claude API Service - handles all interactions with Claude.

This service is pure Python with no Streamlit dependencies,
making it easy to test and reuse across different contexts.
"""

import anthropic
from config.settings import get_settings


class ClaudeService:
    """Service for interacting with Claude API."""

    DISCOVERY_SYSTEM_PROMPT = """You are a friendly cooking assistant helping someone decide what to cook.

Your personality:
- Warm and encouraging, like a friend who loves cooking
- Curious about their preferences and what they're in the mood for
- Helpful in narrowing down choices

IMPORTANT: Your responses will be read aloud by text-to-speech. Do NOT use any markdown formatting. Write in plain, natural sentences.

Your goal is to help them pick a recipe. You can:
- Ask what cuisine, meal type, or mood they're in
- Ask about time available, dietary needs, or ingredients on hand
- If they say "surprise me" or "I don't know", suggest something based on what you've learned or pick a crowd-pleaser
- Describe a recipe in more detail if they ask
- When they decide, confirm and start cooking

IMPORTANT: When the user decides on a recipe, call the select_recipe tool with the recipe ID.

AVAILABLE RECIPES:
{recipe_list}

Keep responses SHORT (1-3 sentences) unless they ask for more detail.
"""

    DISCOVERY_TOOLS = [
        {
            "name": "select_recipe",
            "description": "Select a recipe to start cooking. Call this when the user has decided on a recipe.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "integer",
                        "description": "The ID of the selected recipe"
                    }
                },
                "required": ["recipe_id"]
            }
        }
    ]

    COOKING_SYSTEM_PROMPT = """You are a friendly cooking assistant guiding someone through a recipe step by step.

Your personality:
- Warm and encouraging, like a friend who loves cooking
- Patient with questions and mistakes
- Concise - they're cooking with messy hands
- Practical - offer substitutions, timing tips, and troubleshooting

IMPORTANT: Your responses will be read aloud by text-to-speech. Do NOT use any markdown formatting. Write in plain, natural sentences.

HOW TO HELP:
- Start with prep: help gather ingredients, mention any prep work needed
- Move to cooking when they say "ready" or "let's start"
- Give ONE step at a time, wait for "next" or "what's next"
- If they say "go back" or "repeat", do so
- If they ask to skip ahead or jump to a step, accommodate them
- Answer questions about techniques, timing, or substitutions
- Help troubleshoot ("is it done?", "it looks wrong", "I burned it")
- Convert units if asked (cups to grams, Fahrenheit to Celsius, etc.)
- Scale portions if asked (half batch, double recipe)

Keep responses SHORT (1-3 sentences) unless they ask for detail.

RECIPE:
{recipe_context}
"""

    PLANNING_SYSTEM_PROMPT = """You are a meal planning assistant helping someone plan their meals.

Your personality:
- Friendly and helpful
- Ask clarifying questions about preferences, dietary goals, time constraints
- Only suggest recipes from the AVAILABLE RECIPES list below
- Never invent recipes not in the list

IMPORTANT: Your responses will be read aloud by text-to-speech. Do NOT use any markdown formatting. Write in plain, natural sentences.

HOW TO HELP:
- Ask how many meals they want to plan (a few days, a week, etc.)
- Consider variety: mix cuisines, cooking methods, and ingredients
- Consider practicality: prep time, shared ingredients across meals
- When they confirm choices, create their shopping list

When suggesting recipes, use the add_recipes_to_plan tool with the recipe IDs.

AVAILABLE RECIPES:
{recipe_list}

Keep responses SHORT (1-3 sentences) unless they ask for detail.
"""

    PLANNING_TOOLS = [
        {
            "name": "add_recipes_to_plan",
            "description": "Add one or more recipes to the user's meal plan. Call this whenever you recommend specific recipes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "recipe_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of recipe IDs to add to the plan"
                    }
                },
                "required": ["recipe_ids"]
            }
        }
    ]

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def chat_cooking(
        self,
        message: str,
        recipe_context: str,
        history: list[dict]
    ) -> str:
        """
        Send a message in cooking context.

        Args:
            message: User's message
            recipe_context: Formatted recipe text
            history: List of previous messages [{"role": "user/assistant", "content": "..."}]

        Returns:
            Claude's response text
        """
        messages = history + [{"role": "user", "content": message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.COOKING_SYSTEM_PROMPT.format(recipe_context=recipe_context),
            messages=messages
        )

        return response.content[0].text

    def chat_discovery(
        self,
        message: str,
        recipe_list: str,
        history: list[dict]
    ) -> tuple[str, int | None]:
        """
        Send a message in recipe discovery context with tool calling.

        Args:
            message: User's message
            recipe_list: Formatted list of available recipes
            history: List of previous messages

        Returns:
            Tuple of (response_text, selected_recipe_id or None)
        """
        messages = history + [{"role": "user", "content": message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.DISCOVERY_SYSTEM_PROMPT.format(recipe_list=recipe_list),
            messages=messages,
            tools=self.DISCOVERY_TOOLS
        )

        # Extract text response and tool calls
        response_text = ""
        selected_recipe_id = None

        for block in response.content:
            if block.type == "text":
                response_text = block.text
            elif block.type == "tool_use" and block.name == "select_recipe":
                selected_recipe_id = block.input.get("recipe_id")

        return response_text, selected_recipe_id

    def get_discovery_greeting(self, recipe_list: str) -> str:
        """
        Get an initial greeting for the discovery chat.

        Args:
            recipe_list: Formatted list of available recipes

        Returns:
            Greeting message from Claude
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=self.DISCOVERY_SYSTEM_PROMPT.format(recipe_list=recipe_list),
            messages=[{
                "role": "user",
                "content": "Hi, I want to cook something!"
            }]
        )

        return response.content[0].text

    def chat_planning(
        self,
        message: str,
        recipe_list: str,
        history: list[dict]
    ) -> tuple[str, list[int]]:
        """
        Send a message in meal planning context with tool calling.

        Args:
            message: User's message
            recipe_list: Formatted list of available recipes
            history: List of previous messages

        Returns:
            Tuple of (response_text, list of recipe_ids to add)
        """
        messages = history + [{"role": "user", "content": message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=self.PLANNING_SYSTEM_PROMPT.format(recipe_list=recipe_list),
            messages=messages,
            tools=self.PLANNING_TOOLS
        )

        # Extract text response and tool calls
        response_text = ""
        recipe_ids_to_add = []

        for block in response.content:
            if block.type == "text":
                response_text = block.text
            elif block.type == "tool_use" and block.name == "add_recipes_to_plan":
                recipe_ids_to_add = block.input.get("recipe_ids", [])

        return response_text, recipe_ids_to_add
