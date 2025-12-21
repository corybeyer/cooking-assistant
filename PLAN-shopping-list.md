# Meal Planning & Shopping List Implementation Plan

## Overview

Add meal planning conversation and shopping list with price comparison to the Cooking Assistant.

### User Journey
```
Cooking Assistant → "Plan Meals" button → Meal Planner Chat
    → Conversation with Claude → Meal Plan Confirmed
    → Shopping List Generated → Price Comparison
    → Send to Phone (SMS + checkable web page)
```

---

## Phase 1: Database Schema Updates

### New Tables

```sql
-- Shopping lists (can exist independent of meal plans)
CREATE TABLE ShoppingLists (
    ShoppingListId INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(200) NULL,
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE()),
    Status NVARCHAR(50) NOT NULL DEFAULT 'active'  -- active, completed, archived
);

-- Link shopping lists to recipes (with optional serving multiplier)
CREATE TABLE ShoppingListRecipes (
    ShoppingListRecipeId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    RecipeId INT NOT NULL,
    Servings INT NULL,  -- NULL = use recipe default
    PlannedDate DATE NULL,  -- optional: "Monday dinner"
    MealType NVARCHAR(50) NULL,  -- breakfast, lunch, dinner, snack
    CONSTRAINT FK_ShoppingListRecipes_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE,
    CONSTRAINT FK_ShoppingListRecipes_Recipes
        FOREIGN KEY (RecipeId) REFERENCES Recipes(RecipeId)
);

-- Consolidated shopping list items (aggregated from recipes)
CREATE TABLE ShoppingListItems (
    ShoppingListItemId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    IngredientId INT NOT NULL,
    AggregatedQuantity NVARCHAR(100) NULL,  -- "3 medium" or "2 lbs"
    Category NVARCHAR(50) NULL,  -- produce, meat, dairy, pantry, etc.
    IsChecked BIT NOT NULL DEFAULT 0,
    SortOrder INT NULL,
    CONSTRAINT FK_ShoppingListItems_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE,
    CONSTRAINT FK_ShoppingListItems_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId)
);

-- Price snapshots from grocery APIs
CREATE TABLE GroceryPrices (
    GroceryPriceId INT IDENTITY(1,1) PRIMARY KEY,
    IngredientId INT NOT NULL,
    StoreName NVARCHAR(100) NOT NULL,  -- Kroger, Walmart, H-E-B, etc.
    ProductName NVARCHAR(300) NULL,  -- Actual product matched
    ProductId NVARCHAR(100) NULL,  -- Store's product ID for cart integration
    Price DECIMAL(10,2) NULL,
    Unit NVARCHAR(50) NULL,  -- per lb, each, per oz
    LastUpdated DATETIME NOT NULL DEFAULT(GETDATE()),
    CONSTRAINT FK_GroceryPrices_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId)
);

-- For shareable list links
CREATE TABLE ShoppingListLinks (
    LinkId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    LinkCode NVARCHAR(20) NOT NULL UNIQUE,  -- Short code like "x7k2m"
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE()),
    ExpiresDate DATETIME NULL,
    CONSTRAINT FK_ShoppingListLinks_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE
);
```

### Testing - Phase 1
- [ ] Run schema migration on dev database
- [ ] Verify foreign key constraints work correctly
- [ ] Test cascade deletes (delete shopping list → items deleted)
- [ ] Insert sample data and query to verify relationships

---

## Phase 2: Meal Planner Chat Application

### 2.1 New Streamlit App: `meal_planner.py`

**Location**: `/meal_planner.py` (separate entry point)

**Structure**:
```python
# meal_planner.py
import streamlit as st
from anthropic import Anthropic
from app.database import SessionLocal
from app.models import Recipe, Ingredient

def get_recipe_context():
    """Load all recipes for Claude's context"""
    db = SessionLocal()
    recipes = db.query(Recipe).all()
    # Format as structured text for Claude
    return format_recipes_for_context(recipes)

def main():
    st.set_page_config(page_title="Meal Planner", layout="wide")

    # Initialize chat history
    if "planner_messages" not in st.session_state:
        st.session_state.planner_messages = []

    # System prompt with recipe database context
    system_prompt = f"""
    You are a meal planning assistant. Help the user plan meals
    for the week based on their preferences and dietary goals.

    AVAILABLE RECIPES:
    {get_recipe_context()}

    RULES:
    - Only suggest recipes from the list above
    - Ask clarifying questions about dietary preferences, time constraints
    - When user confirms a plan, format it clearly
    - Ask if they want to generate a shopping list
    """

    # Chat interface
    # ... (standard Streamlit chat implementation)
```

### 2.2 Navigation Button in Cooking Assistant

**Edit**: `streamlit_app.py` sidebar

```python
with st.sidebar:
    st.header("Navigation")

    if st.button("📋 Plan Meals", use_container_width=True):
        # Open meal planner in new tab
        st.markdown(
            '<a href="/meal_planner" target="_blank">Opening Meal Planner...</a>',
            unsafe_allow_html=True
        )
        # Or use JavaScript to open new window
```

### 2.3 Deployment Config Update

Update Container App to serve both apps:
- `/` → Cooking Assistant
- `/planner` → Meal Planner

### Testing - Phase 2
- [ ] Meal planner loads and shows chat interface
- [ ] Claude receives recipe list in context
- [ ] Claude only suggests recipes from database (not invented ones)
- [ ] Conversation flows naturally (preferences → suggestions → confirmation)
- [ ] "Plan Meals" button in main app opens planner
- [ ] Session state persists during conversation

**Test Conversations**:
```
Test 1: "Plan 5 dinners for me"
  → Should ask about preferences before suggesting

Test 2: "I want healthy meals, low carb"
  → Should filter to appropriate recipes

Test 3: "Plan Monday through Friday dinners"
  → Should output in day-of-week format

Test 4: "I want to make Beef Wellington" (not in DB)
  → Should say it's not available, suggest alternatives
```

---

## Phase 3: Shopping List Generation

### 3.1 Ingredient Aggregation Service

**New file**: `app/services/shopping_list.py`

```python
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Recipe, RecipeIngredient, Ingredient, ShoppingList

class ShoppingListService:

    def create_from_recipes(
        self,
        db: Session,
        recipe_ids: List[int],
        servings_multipliers: Dict[int, float] = None
    ) -> ShoppingList:
        """
        Create a shopping list from multiple recipes.
        Aggregates duplicate ingredients.
        """
        pass

    def aggregate_ingredients(
        self,
        db: Session,
        recipe_ids: List[int]
    ) -> List[Dict]:
        """
        Combine ingredients across recipes.
        Returns list of {ingredient, total_quantity, unit, category}
        """
        pass

    def categorize_ingredient(self, ingredient_name: str) -> str:
        """
        Use Claude or rules to categorize: produce, meat, dairy, etc.
        """
        pass
```

### 3.2 Claude-Powered Aggregation

For complex aggregation (unit conversion, vague quantities):

```python
def smart_aggregate_with_claude(ingredients_raw: List[Dict]) -> List[Dict]:
    """
    Send raw ingredients to Claude to intelligently consolidate.

    Input:
    - "1 cup flour" (Recipe A)
    - "2 tablespoons flour" (Recipe B)
    - "onion, diced" (Recipe A)
    - "1 medium onion" (Recipe B)
    - "salt to taste" (Recipe A)
    - "pinch of salt" (Recipe B)

    Output:
    - "Flour: 1 cup + 2 tbsp (about 1⅛ cups)"
    - "Onions: 2 medium"
    - "Salt: (pantry staple)"
    """
    pass
```

### 3.3 Pantry Staples Detection

Ask user once: "Do you usually have these on hand?"
- Salt, pepper, olive oil, butter, garlic, etc.

Store preferences, exclude from list or mark as "check pantry"

### Testing - Phase 3
- [ ] Single recipe → correct shopping list
- [ ] Multiple recipes → ingredients aggregated correctly
- [ ] Same ingredient, same unit → quantities added
- [ ] Same ingredient, different units → converted and combined
- [ ] Vague quantities ("to taste") handled gracefully
- [ ] Categories assigned correctly (produce, meat, etc.)
- [ ] Pantry staples marked appropriately

**Test Cases**:
```
Test: Recipe A (1 onion) + Recipe B (2 onions)
  → Shopping list: "Onions: 3"

Test: Recipe A (1 cup flour) + Recipe B (2 tbsp flour)
  → Shopping list: "Flour: approximately 1⅛ cups"

Test: Recipe A (salt to taste) + Recipe B (1 tsp salt)
  → Shopping list: "Salt: 1 tsp (plus to taste)" or mark as pantry staple
```

---

## Phase 4: Grocery API Integration

### 4.1 API Integrations

**Priority order** (based on API availability):

1. **Kroger** - Best public API
2. **Walmart** - Good affiliate API
3. **Instacart** - Partner API (covers H-E-B, Costco, etc.)

**New file**: `app/services/grocery_apis/`

```
app/services/grocery_apis/
├── __init__.py
├── base.py          # Abstract base class
├── kroger.py        # Kroger API client
├── walmart.py       # Walmart API client
└── instacart.py     # Instacart API client
```

### 4.2 Base Interface

```python
# app/services/grocery_apis/base.py
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ProductMatch:
    store_name: str
    product_id: str
    product_name: str
    price: float
    unit: str  # "each", "per lb", "per oz"
    image_url: Optional[str] = None
    add_to_cart_url: Optional[str] = None

class GroceryAPIBase(ABC):

    @abstractmethod
    def search_product(self, ingredient: str, quantity: str) -> List[ProductMatch]:
        """Search for products matching an ingredient"""
        pass

    @abstractmethod
    def get_cart_url(self, products: List[ProductMatch]) -> str:
        """Generate URL to pre-populated cart"""
        pass
```

### 4.3 Kroger Implementation

```python
# app/services/grocery_apis/kroger.py
import httpx
from app.config import get_settings

class KrogerAPI(GroceryAPIBase):
    BASE_URL = "https://api.kroger.com/v1"

    def __init__(self):
        self.settings = get_settings()
        self.access_token = None

    def authenticate(self):
        """OAuth2 client credentials flow"""
        pass

    def search_product(self, ingredient: str, quantity: str) -> List[ProductMatch]:
        """
        GET /products?filter.term={ingredient}
        Returns matched products with prices
        """
        pass
```

### 4.4 Claude Product Matching

```python
def match_ingredient_to_products(
    ingredient: str,
    quantity: str,
    store_results: Dict[str, List[ProductMatch]]
) -> Dict[str, ProductMatch]:
    """
    Use Claude to pick the best product match from each store.

    Example:
    Ingredient: "Italian sausage (1 lb)"

    Kroger results:
      - "Kroger Italian Sausage Links 16oz" $4.99
      - "Johnsonville Mild Italian 19oz" $5.49
      - "Beyond Meat Italian Sausage 4pk" $7.99

    Claude picks: "Kroger Italian Sausage Links 16oz"
    (closest match to 1 lb, best value)
    """
    pass
```

### 4.5 Price Comparison View

```python
def compare_prices(shopping_list_id: int) -> Dict:
    """
    Returns:
    {
        "items": [
            {
                "ingredient": "Chicken breast",
                "quantity": "2 lbs",
                "prices": {
                    "Kroger": {"price": 8.49, "product": "..."},
                    "Walmart": {"price": 7.98, "product": "..."},
                    "H-E-B": {"price": 7.50, "product": "..."}
                }
            },
            ...
        ],
        "totals": {
            "Kroger": 52.14,
            "Walmart": 47.82,
            "H-E-B": 45.90
        },
        "recommendation": "H-E-B"
    }
    """
    pass
```

### Testing - Phase 4
- [ ] Kroger API authentication works
- [ ] Product search returns results
- [ ] Claude matching selects appropriate products
- [ ] Price comparison calculates correct totals
- [ ] Handle API errors gracefully (store unavailable, rate limits)
- [ ] Cache prices to avoid excessive API calls

**Test Cases**:
```
Test: Search "chicken breast 2 lbs" at Kroger
  → Returns multiple products with prices

Test: Search nonsense ingredient "xyzfooditem"
  → Returns empty gracefully, doesn't crash

Test: Compare prices for 10-item list
  → All stores return totals, sorted by price

Test: One store API fails
  → Other stores still shown, failed store marked "unavailable"
```

### API Keys Required

Add to Azure Key Vault:
- `KROGER_CLIENT_ID`
- `KROGER_CLIENT_SECRET`
- `WALMART_API_KEY`
- `INSTACART_API_KEY` (if partner access granted)

---

## Phase 5: Delivery (SMS + Checkable Web Page)

### 5.1 Azure Communication Services Setup

```python
# app/services/notifications.py
from azure.communication.sms import SmsClient

class NotificationService:

    def send_shopping_list_sms(
        self,
        phone_number: str,
        shopping_list_id: int,
        link_code: str
    ):
        """
        Send SMS with link to shopping list.

        Message:
        "Your shopping list is ready! 13 items for 5 meals.
         View & check off: https://cook.app/list/x7k2m"
        """
        pass
```

### 5.2 Shareable Link Generation

```python
import secrets

def generate_list_link(shopping_list_id: int) -> str:
    """Generate short, unique link code"""
    code = secrets.token_urlsafe(6)  # e.g., "x7k2mN"
    # Store in ShoppingListLinks table
    return f"https://cook.app/list/{code}"
```

### 5.3 Checkable List Web Page

**New Streamlit page or simple Flask route**: `/list/<code>`

```python
# Lightweight page for viewing/checking shopping list
def shopping_list_page(code: str):
    """
    Mobile-optimized page:
    - Shows all items with checkboxes
    - Saves checked state to localStorage (works offline)
    - Optionally syncs back to database
    - Grouped by category (Produce, Meat, Dairy, etc.)
    """
    pass
```

**UI Mockup**:
```
┌─────────────────────────────────┐
│  🛒 Shopping List               │
│  Week of Dec 22 • 13 items      │
├─────────────────────────────────┤
│  PRODUCE                        │
│  ☐ Onions (3)                   │
│  ☑ Lemons (2)                   │
│  ☐ Carrots (4)                  │
│                                 │
│  MEAT                           │
│  ☐ Chicken breast (2 lbs)       │
│  ☐ Italian sausage (1 lb)       │
│                                 │
│  DAIRY                          │
│  ☐ Butter (1 stick)             │
│  ...                            │
├─────────────────────────────────┤
│  [Shop at Kroger] [Shop at H-E-B]│
└─────────────────────────────────┘
```

### Testing - Phase 5
- [ ] SMS sends successfully via Azure Communication Services
- [ ] Link code is unique and retrieves correct list
- [ ] Web page loads on mobile browsers
- [ ] Checkboxes persist state (localStorage)
- [ ] Category grouping displays correctly
- [ ] Page works offline after initial load
- [ ] "Shop at X" buttons open correct store

**Test Cases**:
```
Test: Generate link for shopping list
  → Link code created, stored in DB

Test: Visit link in mobile browser
  → List displays, items checkable

Test: Check 3 items, close browser, reopen
  → Same 3 items still checked

Test: Send SMS to test phone number
  → SMS received with correct link
```

---

## Phase 6: Integration & End-to-End Testing

### Full User Flow Test

```
1. Open Cooking Assistant
2. Click "Plan Meals" → Meal Planner opens
3. Chat: "Plan 5 healthy dinners for the week"
4. Claude suggests recipes, user confirms
5. Click "Generate Shopping List"
6. View aggregated list (13 items)
7. Click "Compare Prices"
8. See comparison: Kroger $52, Walmart $48, H-E-B $46
9. Click "Send to my phone"
10. Enter phone number
11. Receive SMS with link
12. Open link on phone
13. See checkable list, grouped by category
14. Check off items while shopping
15. Click "Shop at H-E-B" → Opens H-E-B/Instacart with cart
```

### Edge Case Tests
- [ ] User with no recipes in database
- [ ] Recipe with missing ingredients
- [ ] Very long shopping list (50+ items)
- [ ] Ingredient not found at any store
- [ ] Invalid phone number
- [ ] Expired shopping list link
- [ ] User goes back and modifies meal plan

### Performance Tests
- [ ] Price comparison completes in <5 seconds
- [ ] SMS delivery within 30 seconds
- [ ] Web page loads in <2 seconds on 3G

---

## Implementation Order

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Database Schema | 1 day | None |
| Phase 2: Meal Planner Chat | 3-4 days | Phase 1 |
| Phase 3: Shopping List Service | 2-3 days | Phase 1 |
| Phase 4: Grocery APIs | 4-5 days | Phase 3, API keys |
| Phase 5: SMS + Web Page | 2-3 days | Phase 3 |
| Phase 6: Integration Testing | 2 days | All phases |

**Total estimated effort**: 2-3 weeks

### Suggested Start Order

1. **Phase 1** - Schema (unblocks everything)
2. **Phase 2 + 3 in parallel** - Chat app + list aggregation
3. **Phase 5** - SMS + web page (can test with mock data)
4. **Phase 4** - Grocery APIs (can work independently)
5. **Phase 6** - Wire everything together

---

## Required API Access

| Service | Action Needed |
|---------|---------------|
| Azure Communication Services | Enable in Azure, get connection string |
| Kroger Developer Portal | Register app, get OAuth credentials |
| Walmart Affiliate Program | Apply for API access |
| Instacart Partner API | Contact for partnership (optional) |

---

## Files to Create/Modify

### New Files
```
meal_planner.py                          # New Streamlit app
app/services/shopping_list.py            # List aggregation
app/services/notifications.py            # SMS sending
app/services/grocery_apis/__init__.py
app/services/grocery_apis/base.py
app/services/grocery_apis/kroger.py
app/services/grocery_apis/walmart.py
app/pages/shopping_list_view.py          # Checkable web page
infrastructure/schema_v2.sql             # New tables
```

### Modified Files
```
streamlit_app.py                         # Add "Plan Meals" button
app/models/entities.py                   # New SQLAlchemy models
app/config.py                            # New API key settings
infrastructure/bicep/modules/keyVault.bicep  # New secrets
requirements.txt                         # Azure Communication SDK
```
