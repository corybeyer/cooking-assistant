"""
Shopping List Page

View and check off items from your shopping lists.
"""

import streamlit as st

st.set_page_config(
    page_title="Shopping List - Cooking Assistant",
    page_icon="🛒",
    layout="wide"
)

from views.shopping_view import ShoppingView

view = ShoppingView()
view.render()
