"""
Cooking Assistant Page

Voice-enabled cooking guidance for recipes.
"""

import streamlit as st

st.set_page_config(
    page_title="Cook - Cooking Assistant",
    page_icon="🍳",
    layout="wide"
)

from views.cooking_view import CookingView

view = CookingView()
view.render()
