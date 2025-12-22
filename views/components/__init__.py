"""
Reusable UI components.
"""

from views.components.chat import render_chat_messages
from views.components.audio import render_mic_button, render_audio_playback
from views.components.shopping_item import render_shopping_item, render_shopping_items_grouped
from views.components.shopping_stats import render_shopping_stats

# Sidebar components
from views.components.sidebar import (
    render_cooking_sidebar,
    render_planning_sidebar,
    render_shopping_list_sidebar,
)

# Share components
from views.components.share import (
    render_email_share,
    render_link_share,
)

__all__ = [
    # Chat & Audio
    "render_chat_messages",
    "render_mic_button",
    "render_audio_playback",
    # Shopping
    "render_shopping_item",
    "render_shopping_items_grouped",
    "render_shopping_stats",
    # Sidebar
    "render_cooking_sidebar",
    "render_planning_sidebar",
    "render_shopping_list_sidebar",
    # Share
    "render_email_share",
    "render_link_share",
]
