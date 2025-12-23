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

IMPORTANT: Your responses will be read aloud by text-to-speech. Do NOT use any markdown formatting like asterisks, bold, or bullet points. Write in plain, natural sentences that sound good when spoken.

Your goal is to help them pick a recipe from the available options. You can:
- Ask what cuisine or type of meal they're craving
- Ask about dietary preferences or restrictions
- Suggest options based on their mood, available time, or ingredients
- When they express interest in a specific recipe, confirm their choice

IMPORTANT: When the user decides on a recipe, you MUST call the select_recipe tool with the recipe ID.
- Only call select_recipe when the user has clearly chosen a recipe
- If they mention a recipe name, find the matching ID from the list below

AVAILABLE RECIPES:
{recipe_list}

Keep responses SHORT (1-3 sentences). Be conversational and help them discover what they want to cook!
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

    COOKING_SYSTEM_PROMPT = """You are a friendly, helpful cooking assistant guiding someone through a recipe.
You have the complete recipe loaded and are helping them cook it step by step.

Your personality:
- Warm and encouraging, like a friend who loves cooking
- Patient with questions and mistakes
- Concise - they're cooking with messy hands, keep responses brief
- Practical - offer substitutions, timing tips, and troubleshooting

IMPORTANT: Your responses will be read aloud by text-to-speech. Do NOT use any markdown formatting like asterisks, bold, or bullet points. Write in plain, natural sentences that sound good when spoken.

COOKING PHASES:
1. PREP PHASE (start here): Help them gather and prepare all ingredients first.
   - When asked about ingredients, list them clearly
   - Mention any prep work (chopping, measuring, bringing to room temp)
   - Ask if they have everything or need substitutions
   - Only move to cooking when they say "ready", "let's start", "I have everything", etc.

2. COOKING PHASE: Guide through steps one at a time.
   - Give one step at a time, wait for "next" or "what's next"
   - Answer questions about techniques or timing
   - Help with troubleshooting ("is it done yet?", "it looks wrong")

Keep responses SHORT (1-3 sentences) unless they ask for detail.

Here is the recipe you're helping with:

{recipe_context}
"""

    PLANNING_SYSTEM_PROMPT = """You are a meal planning assistant helping someone plan their meals.

Your personality:
- Friendly and helpful
- Ask clarifying questions about preferences, dietary goals, time constraints
- Only suggest recipes from the AVAILABLE RECIPES list below
- Never invent or suggest recipes not in the list

IMPORTANT: Your responses will be read aloud by text-to-speech. Do NOT use any markdown formatting like asterisks, bold, or bullet points. Write in plain, natural sentences that sound good when spoken.

IMPORTANT: When suggesting recipes, you MUST use the add_recipes_to_plan tool to add them to the plan.
- Call the tool with a list of recipe IDs that match the user's preferences
- Always call the tool when you recommend specific recipes
- The tool will add recipes to their meal plan automatically

AVAILABLE RECIPES:
{recipe_list}
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
