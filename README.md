# CyberShield

This application is called cyber_shield and it is a Python based application that should have back-end libraries, a server (and database layer), as well as a front-end. Use this information to suggest a new application structure.

#### Setup

To set up the project, follow these steps:

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd cyber_shield
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Codebase Structure

CyberShield has 3 components:

1. The `CyberShield` codebase which is a component of the QMLP
2. The `backend` 
3. The `frontend`

This mimics the setup for QMLP, however, since it is intended to standalone, it will be built in a single repository.

> **Note**
>
> This is a tentative structure of `cyber_shield` Event Detector of the `QMLP` project.

```bash
cyber_shield/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI/Flask app entrypoint
│   │   ├── api/                   # API route definitions
│   │   │   └── routes.py
│   │   ├── models/                # Pydantic/ORM models
│   │   │   └── user.py
│   │   ├── services/              # Business logic (sentiment, abuse detection)
│   │   │   └── text_sniffer.py
│   │   ├── db/                    # Database layer
│   │   │   ├── database.py
│   │   │   └── crud.py
│   │   └── utils/                 # Utility functions
│   │       └── helpers.py
│   ├── requirements.txt
│   └── tests/
│       └── test_text_sniffer.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── README.md
├── data/
│   └── abusive_words.txt
├── scripts/                       # For setup, migrations, etc.
│   └── init_db.py
├── .env
├── README.md
└── abuse_report.json
```

**Notes:**

1. `text_sniffer.py` is where your current logic would go.
2. `backend/app/main.py` is the entrypoint for your API server (e.g., FastAPI or Flask).
3. ` backend/app/db/` handles database connections and CRUD operations. 
4. `frontend/` is for your React/Vue/Angular app. 
5. `data/` holds static files like abusive word lists. 
6. `scripts/` can be used for database migrations or setup scripts.

## Notes

#### Versions of `CyberShield`

There are two versions of `CyberShield`: `cyber_shield` and `cyber_shield_mini`.

#### `cyber_shield/updated_data.json`

`cyber_shield/updated_data.json` from Kaggle (about 3533). Review to see if it can be readily downloadable.

#### Non-standard `text`

Evaluate non-standard presentation of abuse

```json
   "21": {
         "TEXT": "Idi0t f00l.",
         "Sentiment": "Negative",
         "Language": "EN"
   }
```

#### `data_loader` and `sentiment_analyzer_script`

`data_loader`

This currently houses the class responsible for extracting tweets or loading a JSON file containing a list of tweet objects.

`sentiment_analyzer_script`

Also has a routine that will load a file containing tweet objects, which needs to be resolved to a single file, but it serves as a sample on how to utilize the loading mechanisms.

Eventually, it will be the script that does the full `CyberShield` processing once all processing information is moved to a single file.

## FAQ
