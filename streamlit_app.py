"""
Cooking Assistant - Home Page

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

st.title("🍳 Cooking Assistant")
st.markdown("Your AI-powered kitchen companion")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🍳 Cook a Recipe")
    st.markdown("""
    Get voice-guided, step-by-step cooking help.

    - Select a recipe from your collection
    - Ask questions while you cook
    - Get substitution suggestions
    - Hands-free voice control
    """)
    if st.button("Start Cooking →", type="primary", use_container_width=True):
        st.switch_page("pages/1_🍳_Cook.py")

with col2:
    st.markdown("### 📋 Plan Meals")
    st.markdown("""
    Plan your meals for the week with AI help.

    - Chat about dietary preferences
    - Get recipe suggestions
    - Build a meal plan
    - Generate a shopping list
    """)
    if st.button("Plan Meals →", type="primary", use_container_width=True):
        st.switch_page("pages/2_📋_Plan_Meals.py")

st.markdown("---")
st.markdown("*Use the sidebar to navigate between pages.*")
