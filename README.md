# AI Accounts Payable Employee

An autonomous AI agent system for end-to-end Accounts Payable automation, fully compliant with SOX and UK VAT regulations.

## Project Structure

```
ai-ap-employee/
├── app/
│   ├── agents/         # AI Agent implementations
│   ├── api/            # FastAPI routes
│   ├── guardrails/     # Safety and compliance checks
│   ├── memory/         # Context and history management
│   ├── models/         # Pydantic data models
│   ├── tools/          # Integration tools (Gmail, OCR, etc.)
│   ├── workflow/       # LangGraph state machine
│   ├── config.py       # Configuration settings
│   ├── database.py     # Database connection
│   └── main.py         # Application entry point
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── tests/              # Test suite
├── docker-compose.yml  # Container orchestration
└── requirements.txt    # Project dependencies
```

## Setup Instructions

1.  **Clone the repository**
    ```bash
    git clone <repository_url>
    cd ai-ap-employee
    ```

2.  **Environment Setup**
    Create a `.env` file from the example:
    ```bash
    cp .env.example .env
    ```
    Update `.env` with your API keys and configuration.

3.  **Install Dependencies**
    It is recommended to use a virtual environment:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    
    pip install -r requirements.txt
    ```

4.  **Run with Docker**
    Start MongoDB and the application:
    ```bash
    docker-compose up -d
    ```

5.  **Run Locally**
    Ensure MongoDB is running (e.g., via Docker), then start the app:
    ```bash
    uvicorn app.main:app --reload
    ```
    Access the API documentation at `http://localhost:8000/docs`.

## Testing

Run the test suite:
```bash
pytest
```
