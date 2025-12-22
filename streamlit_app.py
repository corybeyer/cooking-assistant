"""
Cooking Assistant - Main Entry Point

A voice-enabled cooking assistant that guides you through recipes
using Claude AI.
"""

import streamlit as st

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Cooking Assistant",
    page_icon="🍳",
    layout="wide"
)

from views.home_view import HomeView

view = HomeView()
view.render()
