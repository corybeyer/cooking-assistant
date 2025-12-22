# Shopping List Feature - Design Document

## Overview

This document captures the goals, decisions, and intent behind the meal planning and shopping list feature for the Cooking Assistant application.

## Problem Statement

Home cooks who plan weekly meals face a fragmented workflow:
1. Decide what to cook (often scattered across recipe sites, cookbooks, notes)
2. Manually compile ingredients from multiple recipes
3. Create a shopping list (often on paper or a notes app)
4. Shop while checking items off (phone in one hand, cart in the other)

We wanted to create a seamless experience from meal planning to shopping.

## Goals

1. **Conversational Meal Planning** - Let users talk with Claude to plan meals for the week, using only recipes from our database (not invented recipes)
2. **Automatic Ingredient Aggregation** - Combine ingredients across multiple recipes intelligently (e.g., "1 cup flour" + "2 cups flour" = "3 cups flour")
3. **Mobile-Friendly Shopping** - Provide a checkable list accessible on any phone while shopping
4. **Shareable Lists** - Send shopping lists via SMS so users don't need to log in at the store

## Architecture Decisions

### MVC Pattern

We refactored from a monolithic `streamlit_app.py` (464 lines) to a strict MVC architecture:

```
cooking-assistant/
├── streamlit_app.py          # Minimal entry point (~20 lines)
├── pages/                    # Streamlit multi-page routing
│   ├── 1_Cook.py
│   ├── 2_Plan_Meals.py
│   └── 3_Shopping_List.py
├── views/                    # UI rendering (Streamlit components)
├── controllers/              # Business logic orchestration
├── services/                 # External integrations (Claude, SMS, DB)
└── app/models/               # SQLAlchemy entities
```

**Why MVC?**
- Clear separation of concerns
- Testable business logic (controllers don't depend on Streamlit)
- Reusable services across different views
- Easier onboarding for new developers

### Managed Identity over Key Vault

For Azure Communication Services authentication, we chose Managed Identity over storing connection strings in Key Vault:

**Managed Identity Benefits:**
- No secrets to store, rotate, or manage
- Credentials handled automatically by Azure
- Simpler configuration (just an endpoint URL)
- More secure (no credentials in config or environment)

**Implementation:**
```python
# Prefers Managed Identity when endpoint is set
if endpoint:
    from azure.identity import DefaultAzureCredential
    credential = DefaultAzureCredential()
    client = SmsClient(endpoint, credential)
elif connection_string:
    # Fallback for local development
    client = SmsClient.from_connection_string(connection_string)
```

### Ingredient Categorization

Shopping lists are organized by store section to minimize backtracking:

| Category | Examples |
|----------|----------|
| Produce | onion, garlic, tomatoes, lettuce |
| Meat & Seafood | chicken, beef, salmon, shrimp |
| Dairy | milk, cheese, butter, eggs |
| Bakery | bread, tortillas, rolls |
| Pantry | flour, sugar, rice, pasta |
| Frozen | ice cream, frozen vegetables |
| Beverages | juice, soda, coffee |

Categories are assigned via a mapping of 70+ common ingredients, with "Other" as fallback.

### Shareable Links

Shopping lists can be shared via:
1. **SMS** - Sends a text with list name, item count, and link
2. **Direct Link** - Copyable URL with expiration

Links use a token-based system stored in `ShoppingListLinks` table with configurable expiration (default: 7 days).

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | MVC Architecture Refactor | Complete |
| 1 | Database Schema (ShoppingLists, Items, Links) | Complete |
| 2 | Meal Planning Page (Claude conversation) | Complete |
| 3 | Shopping List Aggregation Service | Complete |
| 4 | Checkable Shopping List Page | Complete |
| 5 | SMS Delivery via Azure Communication Services | Complete |
| 6 | Grocery Price Comparison | Future |

## Database Schema

New tables added to support shopping lists:

```sql
ShoppingLists        -- List metadata (name, created date, user)
ShoppingListRecipes  -- Many-to-many: which recipes are in each list
ShoppingListItems    -- Individual items with quantity, unit, category, checked status
ShoppingListLinks    -- Shareable tokens with expiration
GroceryPrices        -- Future: price data from multiple grocers
```

## Configuration

### Azure Communication Services

**Option 1: Managed Identity (Production)**
```
AZURE_COMM_ENDPOINT=https://comms-cooking-assistant.communication.azure.com
AZURE_COMM_SENDER_NUMBER=+15125551234
```

**Option 2: Connection String (Local Development)**
```
AZURE_COMM_CONNECTION_STRING=endpoint=https://...;accesskey=...
AZURE_COMM_SENDER_NUMBER=+15125551234
```

### Required Azure Setup

1. Create Azure Communication Services resource
2. Purchase a phone number (Telephony & SMS > Phone numbers)
3. Enable Managed Identity on Container App
4. Grant Container App "Contributor" role on Communication Services resource
5. Set environment variables on Container App

## Future Enhancements

### Phase 6: Grocery Price Comparison

Original vision included comparing prices across grocers (H-E-B, Kroger, Walmart). Challenges:
- H-E-B has no public API
- Would require web scraping or third-party data providers
- Price accuracy and freshness concerns

### Other Ideas

- **Recipe URL Import** - Parse recipes from external websites
- **Pantry Tracking** - Subtract items user already has
- **Meal Plan Templates** - Save and reuse weekly plans
- **Family Sharing** - Multiple users collaborate on same list

## Key Files

| File | Purpose |
|------|---------|
| `services/shopping_list_service.py` | Ingredient aggregation and categorization |
| `services/notification_service.py` | SMS delivery via Azure Communication Services |
| `controllers/shopping_controller.py` | Shopping list business logic |
| `views/shopping_view.py` | Checkable list UI with share options |
| `pages/3_Shopping_List.py` | Streamlit page entry point |
| `infrastructure/schema_shopping_list.sql` | Database DDL for new tables |

## Lessons Learned

1. **Start with MVC** - Refactoring later is painful; structure early
2. **Managed Identity simplifies operations** - No secrets to rotate or leak
3. **Category mapping is never complete** - Need fallback for unknown ingredients
4. **SMS requires phone number purchase** - Not just API setup; budget for monthly cost
5. **Streamlit multi-page apps work well** - Clean navigation without custom routing
