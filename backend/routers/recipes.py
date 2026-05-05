"""
API routes for recipe extraction, history, and meal planning.
"""

import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Recipe
from ..schemas import (
    RecipeRequest,
    RecipeResponse,
    RecipeListItem,
    MealPlanRequest,
    MealPlanResponse,
)
from ..services.scraper import scrape_recipe_page, ScrapingError
from ..services.llm_extractor import extract_recipe_with_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.post("/extract", response_model=RecipeResponse)
def extract_recipe(request: RecipeRequest, db: Session = Depends(get_db)):
    """
    Extract structured recipe data from a blog URL.
    Checks cache first, then scrapes and processes with Gemini.
    """
    url = str(request.url).rstrip("/")

    # Return cached recipe if we have it
    existing = db.query(Recipe).filter(Recipe.url == url).first()
    if existing:
        logger.info(f"Recipe already exists for URL: {url} (id={existing.id})")
        return existing

    # Scrape the webpage
    try:
        scraped_data = scrape_recipe_page(url)
    except ScrapingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected scraping error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape page: {str(e)}")

    # Pass scraped text to Gemini for extraction
    try:
        extracted = extract_recipe_with_llm(scraped_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Recipe extraction failed: {str(e)}")

    # Save to db
    recipe = Recipe(
        url=url,
        title=extracted.get("title", "Untitled Recipe"),
        cuisine=extracted.get("cuisine"),
        prep_time=extracted.get("prep_time"),
        cook_time=extracted.get("cook_time"),
        total_time=extracted.get("total_time"),
        servings=extracted.get("servings"),
        difficulty=extracted.get("difficulty"),
        ingredients=extracted.get("ingredients", []),
        instructions=extracted.get("instructions", []),
        nutrition_estimate=extracted.get("nutrition_estimate"),
        substitutions=extracted.get("substitutions", []),
        shopping_list=extracted.get("shopping_list", {}),
        related_recipes=extracted.get("related_recipes", []),
        raw_content=scraped_data.get("text", "")[:50000],  # Truncate raw content
    )

    try:
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        logger.info(f"Saved recipe: {recipe.title} (id={recipe.id})")
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save recipe to database.")

    return recipe


@router.get("", response_model=list[RecipeListItem])
def list_recipes(db: Session = Depends(get_db)):
    """
    List all saved recipes (lightweight summary for history table).
    Ordered by most recently created first.
    """
    recipes = (
        db.query(Recipe)
        .order_by(Recipe.created_at.desc())
        .all()
    )
    return recipes


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get full recipe details by ID."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe with id {recipe_id} not found.")
    return recipe


@router.post("/meal-plan", response_model=MealPlanResponse)
def generate_meal_plan(request: MealPlanRequest, db: Session = Depends(get_db)):
    """
    Generate a combined meal plan from selected recipes.
    Merges shopping lists and calculates total nutrition.
    """
    recipes = (
        db.query(Recipe)
        .filter(Recipe.id.in_(request.recipe_ids))
        .all()
    )

    if not recipes:
        raise HTTPException(status_code=404, detail="No recipes found for the given IDs.")

    if len(recipes) != len(request.recipe_ids):
        found_ids = {r.id for r in recipes}
        missing = [rid for rid in request.recipe_ids if rid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Some recipes not found. Missing IDs: {missing}",
        )

    # Merge shopping lists from all selected recipes
    merged = defaultdict(list)
    for recipe in recipes:
        if recipe.shopping_list:
            for category, items in recipe.shopping_list.items():
                for item in items:
                    item_lower = item.strip().lower()
                    # Avoid duplicates (case-insensitive)
                    if item_lower not in [i.lower() for i in merged[category]]:
                        merged[category].append(item.strip())

    # Aggregate total nutrition
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0

    for recipe in recipes:
        if recipe.nutrition_estimate:
            n = recipe.nutrition_estimate
            total_calories += _parse_number(n.get("calories", 0))
            total_protein += _parse_number(n.get("protein", "0g"))
            total_carbs += _parse_number(n.get("carbs", "0g"))
            total_fat += _parse_number(n.get("fat", "0g"))

    # Build the final meal plan response
    return MealPlanResponse(
        recipes=[
            {"id": r.id, "title": r.title, "servings": r.servings}
            for r in recipes
        ],
        merged_shopping_list=dict(merged),
        total_nutrition={
            "calories": round(total_calories),
            "protein": f"{round(total_protein)}g",
            "carbs": f"{round(total_carbs)}g",
            "fat": f"{round(total_fat)}g",
        },
    )


def _parse_number(value) -> float:
    """Extract a numeric value from strings like '12g', '350', etc."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        match = re.search(r"[\d.]+", value)
        return float(match.group()) if match else 0.0
    return 0.0
