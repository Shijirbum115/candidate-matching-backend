# Hybrid Candidate Search System - Usage Instructions

## Setup

1. **Create environment file**:

Create a `.env` file in the project root with the following variables:

```
# Database configuration
PG_DB_HOST=localhost
PG_DB_PORT=5432
PG_DB_NAME=hmcs_db
PG_DB_USER=postgres
PG_DB_PASSWORD=your_password

# OpenAI configuration
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-large
TRANSLATION_MODEL=gpt-3.5-turbo

# Search configuration
DEFAULT_SEARCH_LIMIT=20
DEFAULT_SCORE_THRESHOLD=0.3
DEFAULT_EXPERIENCE_WEIGHT_MULTIPLIER=2.0
DEFAULT_MN_KEYWORD_WEIGHT=1.0
DEFAULT_EN_KEYWORD_WEIGHT=1.0
DEFAULT_SEMANTIC_WEIGHT=1.0

# Logging configuration
LOG_LEVEL=INFO
LOG_DIR=logs

# CORS configuration
CORS_ORIGINS=*
```

2. **Create virtual environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install fastapi uvicorn psycopg2-binary python-dotenv requests pydantic
```

## Running the Application

1. **Start the application**:

```bash
python -m app.main
```

The application will be available at http://localhost:8000.

2. **API Documentation**:

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Using the Search API

### Example Request

```bash
curl -X 'POST' \
  'http://localhost:8000/api/search' \
  -H 'Content-Type: application/json' \
  -d '{
    "query_mn": "5+ жилийн туршлагатай Python хөгжүүлэгч",
    "min_years_exp": 3,
    "max_years_exp": null,
    "limit": 10,
    "score_threshold": 0.3,
    "experience_weight_multiplier": 2.0,
    "mn_keyword_weight": 1.0,
    "en_keyword_weight": 1.0,
    "semantic_weight": 1.2
  }'
```

### Example Response

```json
{
  "candidates": [
    {
      "id": 1045,
      "first_name": "Bat",
      "last_name": "Bold",
      "total_years_experience": 7.5,
      "scores": {
        "mn_keyword_score": 0.89,
        "en_keyword_score": 0.75,
        "semantic_score": 0.92,
        "experience_factor": 2.0,
        "final_score": 0.85
      },
      "explanation": "Bat Bold has 7.5 years of total experience. Positions include: Senior Python Developer and 1 more. Skills include: Python, Django, FastAPI and 2 more. Meets the required 5+ years of experience. Has an excellent semantic match (0.92) with the search query. Contains many of the exact keywords from the query (MN: 0.89, EN: 0.75). Position title matches the search query: Senior Python Developer.",
      "position_titles": ["Senior Python Developer", "Backend Developer"],
      "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "AWS"]
    },
    ...
  ],
  "query_params": {
    "original_query": "5+ жилийн туршлагатай Python хөгжүүлэгч",
    "translated_query": "Python developer with 5+ years of experience",
    "extracted_params": {
      "job_title": "Python хөгжүүлэгч",
      "industry": null,
      "experience_years": 5
    }
  },
  "total_candidates_processed": 120,
  "total_candidates_after_filtering": 10,
  "processing_time_ms": 3245.67
}
```

## Monitoring Search Performance

The system generates detailed logs in the `logs` directory:

1. **General application logs**: `logs/YYYY-MM-DD_app.log`
2. **Search metrics logs**: `logs/YYYY-MM-DD_search_metrics.json`

The search metrics log contains detailed information about each search, including:
- Original and translated queries
- Number of candidates processed and returned
- Processing time
- Scoring weights used
- Detailed candidate scores

Example search metrics log entry:

```json
{
  "timestamp": "2023-04-29T14:35:21.456789",
  "query": "5+ жилийн туршлагатай Python хөгжүүлэгч",
  "query_en": "Python developer with 5+ years of experience",
  "num_candidates_processed": 120,
  "num_results_returned": 10,
  "processing_time_ms": 3245.67,
  "score_threshold": 0.3,
  "weights": {
    "mn_keyword": 1.0,
    "en_keyword": 1.0,
    "semantic": 1.2,
    "experience_multiplier": 2.0
  },
  "candidates": [
    {
      "id": 1045,
      "name": "Bat Bold",
      "experience_years": 7.5,
      "raw_scores": {
        "mn_keyword": 0.8,
        "en_keyword": 0.65,
        "semantic": 0.87
      },
      "normalized_scores": {
        "mn_keyword": 0.89,
        "en_keyword": 0.75,
        "semantic": 0.92
      },
      "experience_factor": 2.0,
      "final_score": 0.85,
      "position_titles": ["Senior Python Developer", "Backend Developer"],
      "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "AWS"],
      "passed_threshold": true
    },
    ...
  ]
}
```

## Tuning Search Performance

To adjust the search algorithm:

1. **Modify search weights**: Adjust the weight parameters in your request to emphasize different search aspects:
   - `mn_keyword_weight`: Increase to prioritize matches in the original Mongolian text
   - `en_keyword_weight`: Increase to prioritize English keyword matches
   - `semantic_weight`: Increase to prioritize semantic similarity
   - `experience_weight_multiplier`: Increase to give more weight to experienced candidates

2. **Adjust score threshold**: Change the `score_threshold` parameter to control the minimum match quality

3. **Experience filtering**: Use `min_years_exp` and `max_years_exp` to filter candidates by experience
