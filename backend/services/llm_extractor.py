"""
LLM-based recipe extraction using LangChain + Google Gemini.

Takes scraped page data (JSON-LD and/or raw text) and uses Gemini
to extract structured recipe information, nutritional estimates,
substitutions, shopping lists, and related recipe suggestions.
"""

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from ..config import settings

logger = logging.getLogger(__name__)


# Schemas for structured output

class IngredientExtracted(BaseModel):
    """A single ingredient with quantity, unit, and item separated."""
    quantity: str = Field(description="Numeric quantity, e.g. '2'. Empty string if none")
    unit: str = Field(description="Unit, e.g. 'cups'. Empty string if none")
    item: str


class NutritionExtracted(BaseModel):
    """Approximate nutritional information per serving."""
    calories: int
    protein: str
    carbs: str
    fat: str


class RecipeExtracted(BaseModel):
    """Complete structured recipe data extracted by the LLM."""
    title: str
    cuisine: str
    prep_time: str
    cook_time: str
    total_time: str
    servings: int
    difficulty: str = Field(description="Must be 'easy', 'medium', or 'hard'.")
    ingredients: list[IngredientExtracted]
    instructions: list[str]
    nutrition_estimate: NutritionExtracted
    substitutions: list[str] = Field(description="Exactly 3 ingredient substitution suggestions referencing actual ingredients from the recipe.")
    shopping_list: dict[str, list[str]] = Field(description="Ingredients grouped by shopping category (e.g. 'dairy', 'produce', 'pantry', 'bakery', 'meat', 'spices').")
    related_recipes: list[str] = Field(description="Exactly 3 related recipe names that pair well with this dish.")


# Prompt templates

EXTRACTION_PROMPT = """You are a professional chef and nutritionist. Analyze the following recipe page content and extract structured recipe information.

IMPORTANT RULES:
1. ONLY use information that is present in or can be directly inferred from the provided content. Do NOT invent or hallucinate recipe details.
2. For ingredients, carefully separate the quantity (number), unit (measurement), and item (ingredient name). If quantity or unit is not specified, use an empty string.
3. For nutritional estimates, provide reasonable approximations based on standard USDA nutritional data for the ingredients and quantities listed. These are estimates, not exact values.
4. For substitutions, suggest exactly 3 practical alternatives that reference ACTUAL ingredients from this specific recipe. Each substitution should explain the benefit (e.g., dietary, health, flavor).
5. For the shopping list, categorize ALL ingredients from the recipe into logical grocery store sections.
6. For related recipes, suggest exactly 3 dishes that would complement this recipe as part of a meal.
7. Difficulty should be "easy" (< 30 min, simple techniques), "medium" (30-60 min or moderate techniques), or "hard" (> 60 min or advanced techniques).

{content_section}

Extract the complete structured recipe data from the above content."""


def _build_content_section(scraped_data: dict) -> str:
    parts = []

    if scraped_data.get("json_ld"):
        parts.append("=== STRUCTURED RECIPE DATA (JSON-LD) ===")
        parts.append(json.dumps(scraped_data["json_ld"], indent=2, default=str))
        parts.append("")

    if scraped_data.get("text"):
        parts.append("=== PAGE TEXT CONTENT ===")
        parts.append(scraped_data["text"])

    return "\n".join(parts)


def extract_recipe_with_llm(scraped_data: dict) -> dict:
    """
    Use Gemini via LangChain to extract structured recipe data from scraped content.

    Args:
        scraped_data: Dict with 'json_ld' (optional) and 'text' keys from scraper.

    Returns:
        Dict matching the RecipeExtracted schema.

    Raises:
        ValueError: If LLM extraction fails or returns invalid data.
    """
    if not settings.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Please add it to your .env file. "
            "Get a free key at https://aistudio.google.com/"
        )

    # Initialize the Gemini model via LangChain
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,  # Low temperature for consistent, factual extraction
    )

    # Use structured output for reliable JSON responses
    structured_llm = llm.with_structured_output(RecipeExtracted)

    # Build the prompt with scraped content
    content_section = _build_content_section(scraped_data)
    prompt = EXTRACTION_PROMPT.format(content_section=content_section)

    logger.info(f"Sending extraction request to Gemini ({settings.GEMINI_MODEL})...")

    try:
        result: RecipeExtracted = structured_llm.invoke(prompt)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"LLM extraction failed: {error_msg}")

        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise ValueError(
                "Gemini API rate limit reached. The free tier has limited requests per minute. "
                "Please wait a moment and try again."
            )
        elif "API key" in error_msg or "401" in error_msg or "403" in error_msg:
            raise ValueError(
                "Invalid Gemini API key. Please check your GOOGLE_API_KEY in the .env file."
            )
        else:
            raise ValueError(f"LLM extraction failed: {error_msg}")

    # Convert Pydantic model to dict for storage
    extracted = result.model_dump()

    logger.info(f"Successfully extracted recipe: {extracted.get('title', 'Unknown')}")
    return extracted
