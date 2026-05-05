# Recipe Extractor & Meal Planner

An AI-powered web application that extracts structured recipe data from blog URLs, generates nutritional estimates, ingredient substitutions, shopping lists, and related recipe suggestions.

## Features

- **Recipe Extraction**: Paste any recipe blog URL and get structured data extracted by AI
- **Smart Scraping**: Two-tier approach — JSON-LD structured data first, fallback to full-text extraction
- **AI-Powered Analysis**: Uses Google Gemini (via LangChain) for intelligent extraction
- **Nutritional Estimates**: Approximate calories, protein, carbs, and fat per serving
- **Ingredient Substitutions**: 3 practical alternatives for dietary/health needs
- **Shopping List**: Ingredients grouped by grocery store category
- **Related Recipes**: 3 complementary dish suggestions
- **Recipe History**: All extracted recipes stored in PostgreSQL
- **Meal Planner**: Select 2–5 saved recipes to generate a merged shopping list
- **Beautiful UI**: Dark theme with glassmorphism, animations, and responsive design

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Frontend | Vanilla HTML / CSS / JavaScript |
| LLM | Google Gemini 2.5 Flash via LangChain |
| Scraping | BeautifulSoup + lxml |

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Google Gemini API key ([get one free](https://aistudio.google.com/))

### 1. Create the Database

```bash
psql -U postgres -c "CREATE DATABASE recipe_planner;"
```

### 2. Configure Environment

Create a `.env` file in the project root (see `.env.example`):

```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/recipe_planner
GOOGLE_API_KEY=your-gemini-api-key
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Run the Server

```bash
cd recipe-planner
uvicorn backend.main:app --reload --port 8000
```

### 5. Open the App

Visit [http://localhost:8000](http://localhost:8000)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/recipes/extract` | Extract recipe from URL `{"url": "..."}` |
| `GET` | `/api/recipes` | List all saved recipes |
| `GET` | `/api/recipes/{id}` | Get full recipe by ID |
| `POST` | `/api/recipes/meal-plan` | Generate meal plan `{"recipe_ids": [1,2,3]}` |
| `GET` | `/api/health` | Health check |

## Project Structure

```
recipe-planner/
├── backend/
│   ├── main.py              # FastAPI app entrypoint
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   └── recipes.py       # API routes
│   ├── services/
│   │   ├── scraper.py       # BeautifulSoup scraping
│   │   └── llm_extractor.py # LangChain + Gemini
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── prompts/                 # LangChain prompt templates
├── sample_data/             # Example URLs and JSON outputs
├── screenshots/             # UI screenshots
├── .env.example
└── README.md
```

## Testing

1. Start the server: `uvicorn backend.main:app --reload`
2. Open http://localhost:8000
3. **Tab 1**: Paste a recipe URL (e.g., `https://www.allrecipes.com/recipe/23891/grilled-cheese-sandwich/`)
4. Click "Extract Recipe" — wait 15-30 seconds for AI processing
5. **Tab 2**: View saved recipes, click "Details" for full view
6. Select 2+ recipes and click "Generate Meal Plan"

## Prompt Templates

See the `prompts/` directory for the LangChain prompt templates used:
- `recipe_extraction.txt` — Structured recipe extraction
- `nutrition_estimation.txt` — Nutritional estimate generation
- `substitution_generation.txt` — Substitutions, shopping list, and related recipes
- `meal_planning.txt` — Meal planning and merged shopping lists

## Error Handling

- Invalid URLs → 400 error with descriptive message
- Non-recipe pages → Graceful fallback with error notification
- Duplicate URLs → Returns cached result from database
- API rate limits → User-friendly rate limit message
- Network errors → Toast notification with retry guidance
