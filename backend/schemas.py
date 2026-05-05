"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


#  Request schemas 

class RecipeRequest(BaseModel):
    """Request body for the extract endpoint."""
    url: HttpUrl


class MealPlanRequest(BaseModel):
    """Request body for the meal planner endpoint."""
    recipe_ids: list[int] = Field(..., min_length=1, max_length=10)


#  Ingredient sub-schema 

class IngredientItem(BaseModel):
    quantity: str = ""
    unit: str = ""
    item: str


#  Nutrition sub-schema 

class NutritionEstimate(BaseModel):
    calories: int | float = 0
    protein: str = "0g"
    carbs: str = "0g"
    fat: str = "0g"


#  Full recipe response 

class RecipeResponse(BaseModel):
    """Complete recipe data returned by the API."""
    id: int
    url: str
    title: str
    cuisine: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    servings: Optional[int] = None
    difficulty: Optional[str] = None
    ingredients: list[IngredientItem] = []
    instructions: list[str] = []
    nutrition_estimate: Optional[NutritionEstimate] = None
    substitutions: list[str] = []
    shopping_list: dict[str, list[str]] = {}
    related_recipes: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


#  History list item (lightweight) 

class RecipeListItem(BaseModel):
    """Lightweight recipe summary for the history table."""
    id: int
    title: str
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


#  Meal plan response 

class MealPlanResponse(BaseModel):
    """Merged shopping list and recipe summaries for meal planning."""
    recipes: list[dict]  # [{id, title, servings}, ...]
    merged_shopping_list: dict[str, list[str]]
    total_nutrition: dict[str, str | int | float]
