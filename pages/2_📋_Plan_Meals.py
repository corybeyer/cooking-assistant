"""
Meal Planner Page

Chat with Claude to plan your meals and create shopping lists.
"""

import streamlit as st

st.set_page_config(
    page_title="Meal Planner - Cooking Assistant",
    page_icon="📋",
    layout="wide"
)

from views.planning_view import PlanningView

view = PlanningView()
view.render()
