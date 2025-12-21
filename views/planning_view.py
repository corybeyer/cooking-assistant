"""
Planning View - UI for meal planning conversations.

This view handles all rendering for the meal planning feature.
It delegates business logic to the PlanningController.
"""

import streamlit as st

from controllers.planning_controller import PlanningController


class PlanningView:
    """View for meal planning UI."""

    def __init__(self):
        self.controller = PlanningController()

    def render(self):
        """Main render method."""
        st.title("📋 Meal Planner")
        st.markdown("Chat with me to plan your meals for the week!")

        # Sidebar with recipe selection and plan summary
        self._render_sidebar()

        # Main chat area
        self._render_chat_area()

    def _render_sidebar(self):
        """Render sidebar with plan summary and controls."""
        with st.sidebar:
            st.markdown("### 🍽️ Your Plan")
            st.markdown("---")

            # Show selected recipes
            selected = self.controller.get_selected_recipe_details()

            if selected:
                for recipe in selected:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {recipe.name}")
                    with col2:
                        if st.button("✕", key=f"remove_{recipe.id}", help="Remove"):
                            self.controller.remove_recipe_from_plan(recipe.id)
                            st.rerun()

                st.markdown("---")

                # Confirm plan button
                if not self.controller.is_plan_confirmed():
                    plan_name = st.text_input(
                        "Plan name (optional):",
                        placeholder="e.g., Healthy Week"
                    )

                    if st.button("✅ Confirm Plan & Create Shopping List",
                                type="primary",
                                use_container_width=True):
                        try:
                            list_id = self.controller.confirm_plan(plan_name or None)
                            st.success(f"Shopping list created!")
                            st.info("Go to the Shopping List page to view and share it.")
                        except ValueError as e:
                            st.error(str(e))
                else:
                    st.success("✅ Plan confirmed!")
                    list_id = self.controller.get_shopping_list_id()
                    st.info(f"Shopping list #{list_id} created")

                    if st.button("🆕 Start New Plan", use_container_width=True):
                        self.controller.clear_conversation()
                        st.rerun()
            else:
                st.markdown("*No recipes selected yet.*")
                st.markdown("Chat with me to get meal suggestions!")

            st.markdown("---")

            # Quick add section
            st.markdown("### ➕ Quick Add")
            all_recipes = self.controller.get_all_recipes()

            if all_recipes:
                recipe_names = {r.name: r.id for r in all_recipes}
                selected_name = st.selectbox(
                    "Add a recipe:",
                    options=[""] + list(recipe_names.keys()),
                    format_func=lambda x: "Select..." if x == "" else x,
                    label_visibility="collapsed"
                )

                if selected_name:
                    if st.button("Add to Plan", use_container_width=True):
                        self.controller.add_recipe_to_plan(recipe_names[selected_name])
                        st.rerun()

            st.markdown("---")

            # Clear conversation
            if st.button("🗑️ Clear Conversation", use_container_width=True):
                self.controller.clear_conversation()
                st.rerun()

    def _render_chat_area(self):
        """Render main chat area."""
        messages = self.controller.get_messages()

        # Start conversation if empty
        if not messages:
            with st.spinner("Starting conversation..."):
                self.controller.start_conversation()
                st.rerun()

        # Display chat messages
        chat_container = st.container(height=450)
        with chat_container:
            for msg in messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Chat input
        st.markdown("---")

        user_input = st.chat_input("Type your message...")

        if user_input:
            with st.spinner("Thinking..."):
                self.controller.send_message(user_input)
            st.rerun()

        # Quick prompts
        st.markdown("**Quick prompts:**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🥗 Healthy meals", use_container_width=True):
                self.controller.send_message("I want healthy, nutritious meals")
                st.rerun()

        with col2:
            if st.button("⏱️ Quick & easy", use_container_width=True):
                self.controller.send_message("I need quick meals under 30 minutes")
                st.rerun()

        with col3:
            if st.button("🎉 Special occasion", use_container_width=True):
                self.controller.send_message("I'm planning for a special occasion")
                st.rerun()
