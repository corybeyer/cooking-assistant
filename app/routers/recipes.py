from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Recipe, Ingredient, UnitOfMeasure, RecipeIngredient, Step
from app.schemas import RecipeCreate, RecipeSummary, RecipeDetail, IngredientResponse, StepResponse

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeSummary])
def list_recipes(
    skip: int = 0,
    limit: int = 50,
    cuisine: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db)
):
    """List all recipes with optional filtering."""
    query = select(Recipe)

    if cuisine:
        query = query.where(Recipe.Cuisine == cuisine)
    if category:
        query = query.where(Recipe.Category == category)

    query = query.offset(skip).limit(limit)
    recipes = db.scalars(query).all()

    return [
        RecipeSummary(
            recipe_id=r.RecipeId,
            name=r.Name,
            description=r.Description,
            cuisine=r.Cuisine,
            category=r.Category,
            prep_time=r.PrepTime,
            cook_time=r.CookTime,
            servings=r.Servings,
            created_date=r.CreatedDate
        )
        for r in recipes
    ]


@router.get("/{recipe_id}", response_model=RecipeDetail)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get a recipe with all ingredients and steps."""
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Build ingredient list
    ingredients = [
        IngredientResponse(
            order_index=ri.OrderIndex,
            name=ri.ingredient.Name,
            quantity=ri.Quantity,
            unit=ri.unit.UnitName if ri.unit else None
        )
        for ri in sorted(recipe.ingredients, key=lambda x: x.OrderIndex)
    ]

    # Build step list
    steps = [
        StepResponse(
            step_id=s.StepId,
            order_index=s.OrderIndex,
            description=s.Description
        )
        for s in recipe.steps  # Already ordered by relationship
    ]

    return RecipeDetail(
        recipe_id=recipe.RecipeId,
        name=recipe.Name,
        description=recipe.Description,
        source_type=recipe.SourceType,
        source_url=recipe.SourceURL,
        cuisine=recipe.Cuisine,
        category=recipe.Category,
        prep_time=recipe.PrepTime,
        cook_time=recipe.CookTime,
        servings=recipe.Servings,
        created_date=recipe.CreatedDate,
        ingredients=ingredients,
        steps=steps
    )


@router.post("", response_model=RecipeDetail, status_code=201)
def create_recipe(recipe_data: RecipeCreate, db: Session = Depends(get_db)):
    """Create a new recipe with ingredients and steps."""

    # Create the recipe
    recipe = Recipe(
        Name=recipe_data.name,
        Description=recipe_data.description,
        SourceType=recipe_data.source_type,
        SourceURL=recipe_data.source_url,
        Cuisine=recipe_data.cuisine,
        Category=recipe_data.category,
        PrepTime=recipe_data.prep_time,
        CookTime=recipe_data.cook_time,
        Servings=recipe_data.servings
    )
    db.add(recipe)
    db.flush()  # Get the RecipeId

    # Process ingredients
    for idx, ing_data in enumerate(recipe_data.ingredients, start=1):
        # Get or create ingredient
        ingredient = db.scalar(
            select(Ingredient).where(Ingredient.Name == ing_data.name)
        )
        if not ingredient:
            ingredient = Ingredient(Name=ing_data.name)
            db.add(ingredient)
            db.flush()

        # Get or create unit
        unit = None
        if ing_data.unit:
            unit = db.scalar(
                select(UnitOfMeasure).where(UnitOfMeasure.UnitName == ing_data.unit)
            )
            if not unit:
                unit = UnitOfMeasure(UnitName=ing_data.unit)
                db.add(unit)
                db.flush()

        # Create recipe-ingredient link
        recipe_ingredient = RecipeIngredient(
            RecipeId=recipe.RecipeId,
            IngredientId=ingredient.IngredientId,
            UnitId=unit.UnitId if unit else None,
            Quantity=ing_data.quantity,
            OrderIndex=idx
        )
        db.add(recipe_ingredient)

    # Process steps
    for idx, step_data in enumerate(recipe_data.steps, start=1):
        step = Step(
            RecipeId=recipe.RecipeId,
            Description=step_data.description,
            OrderIndex=idx
        )
        db.add(step)

    db.commit()
    db.refresh(recipe)

    # Return the created recipe
    return get_recipe(recipe.RecipeId, db)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Delete a recipe (cascades to ingredients and steps)."""
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    db.delete(recipe)
    db.commit()
