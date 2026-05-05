"""
SQLAlchemy ORM models for the Recipe Planner database.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from .database import Base


class Recipe(Base):
    """
    Stores all extracted and generated recipe data.
    JSON columns hold structured data (ingredients list, nutrition dict, etc.)
    to keep the schema simple while supporting complex nested data.
    """
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    cuisine = Column(String(128), nullable=True)
    prep_time = Column(String(64), nullable=True)
    cook_time = Column(String(64), nullable=True)
    total_time = Column(String(64), nullable=True)
    servings = Column(Integer, nullable=True)
    difficulty = Column(String(32), nullable=True)  # easy, medium, hard

    # Complex structured data stored as JSON
    ingredients = Column(JSON, nullable=False, default=list)       # [{quantity, unit, item}, ...]
    instructions = Column(JSON, nullable=False, default=list)      # [str, ...]
    nutrition_estimate = Column(JSON, nullable=True)                # {calories, protein, carbs, fat}
    substitutions = Column(JSON, nullable=True, default=list)      # [str, ...]
    shopping_list = Column(JSON, nullable=True, default=dict)      # {category: [items]}
    related_recipes = Column(JSON, nullable=True, default=list)    # [str, ...]

    # Raw scraped content for debugging/re-processing
    raw_content = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<Recipe(id={self.id}, title='{self.title}')>"
