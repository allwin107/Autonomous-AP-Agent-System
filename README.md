# AI Accounts Payable Employee

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An autonomous, multi-agent AI system designed to handle the end-to-end Accounts Payable (AP) lifecycle. The system automates ingestion, extraction, validation, 3-way matching, and payment preparation while maintaining enterprise-grade guardrails and compliance.

## Features

- **7 Core Scenarios**: Production-tested handling for duplicates, PO mismatches, bank changes, and VAT errors.
- **Multi-Agent Orchestration**: Powered by LangGraph for stateful, cyclic AI expert collaboration.
- **Production Guardrails**: 4-layer safety system including RBAC, fraud detection, and immutable audit trails.
- **Memory & Learning**: 3-layer memory architecture (Episodic, Semantic, Reflection) that improves accuracy over time.
- **Config-Driven**: Multi-tenant architecture for rapid onboarding (< 15 mins).

## Architecture

Our system uses a specialized agent network coordinated by a central LangGraph state machine.

- **Technical Deep-Dive**: [Technical Design Document](docs/technical_design_document.md)
- **Data Model**: [ERD Diagram](docs/erd.md)

## Tech Stack

- **Core**: Python 3.11+, FastAPI
- **Intelligence**: Groq (Llama 3.1), LangGraph
- **Database**: MongoDB 7.0 (GridFS + Vector Search)
- **Tooling**: Tesseract OCR, Pydantic v2

## Prerequisites

- **Docker & Docker Compose**
- **Python 3.11+**
- **Groq API Key**: Get one at [groq.com](https://groq.com)
- **Gmail Account**: (Optional) For automated ingestion demo

## Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/allwin107/Autonomous-AP-Agent-System.git
cd Autonomous-AP-Agent-System
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

### 2. Install Dependencies
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Start Services
```bash
# Start MongoDB
docker-compose up -d

# Initialize DB & Seed Sample Data
python scripts/init_db.py
python scripts/seed_data.py
```

### 4. Run Application
```bash
uvicorn app.main:app --reload
```

Visit the interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Configuration

### Gmail Setup (Ingestion)
1. Create a Google Cloud project and enable the Gmail API.
2. Create OAuth2 credentials and download the `credentials.json`.
3. Run the setup script:
   ```bash
   python scripts/setup_gmail.py
   ```

### Company Policies
Configure company-specific tolerances and approval limits:
```bash
python scripts/configure_company.py --company acme_corp
```

## Running Tests

The system comes with a comprehensive suite of 56 tests (Unit, Integration, Scenario, Performance):

```bash
# Run all tests with coverage
pytest tests/ --cov=app --vv
```

## Demo Scenarios

Run specific end-to-end scenarios to see the agents in action:
```bash
# Explore all demo capabilities
python scripts/run_demo.py --scenario all
```

## API & UI

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Approval Portal**: [http://localhost:8000/ui/approvals](http://localhost:8000/ui/approvals)
- **Monitoring Dashboard**: [http://localhost:8000/ui/monitoring](http://localhost:8000/ui/monitoring)

## Project Structure

```text
Autonomous-AP-Agent-System/
├── app/
│   ├── agents/         # AI Agent expert logic (Extraction, Validation, etc.)
│   ├── api/            # FastAPI routes & UI dashboard endpoints
│   ├── guardrails/     # Safety, Audit & Permission layers
│   ├── memory/         # Context management & Semantic memory
│   ├── models/         # Pydantic data schemas & persistence models
│   ├── monitoring/     # SLA tracking & pipeline health metrics
│   ├── repositories/   # Database abstraction & CRUD logic
│   ├── tools/          # External tools (OCR, Gmail, VAT, Payments)
│   └── workflow/       # LangGraph orchestration & state definitions
├── docs/               # Technical Design, ERD & Demo guides (Internal)
├── scripts/            # Setup, seeding, & scenario demonstration utilities
├── templates/          # Jinja2 templates for HR-friendly dashboards
├── tests/              # Multi-tier suite (unit, integration, scenarios)
├── Dockerfile          # Containerized deployment manifest
└── docker-compose.yml  # Local multi-service orchestration (Mongo + App)
```

## License

MIT: [MIT](LICENSE)

## Contact

- **Email**: allwin10raja@gmail.com
- **GitHub**: [allwin107](https://github.com/allwin107)
- **LinkedIn**: [allwin-raja](https://www.linkedin.com/in/allwin-raja/)
- **Portfolio**: [Allwin Raja](https://portfolio-wine-rho-1jwllmag7n.vercel.app//)
