# E-Commerce AI Customer Support Agent

A production-grade AI-powered customer support agent built with LangGraph, FastAPI, and PostgreSQL. The agent handles order-related queries, detects delayed orders, and proposes cancellations or refunds with mandatory human approval.

## Architecture

The system follows a modular architecture with strict separation of concerns:

```
User Request → FastAPI → LangGraph Agent → [Classify → Fetch Data → RAG → Reasoning → Guardrails → Approval → Execute] → Response
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic
- **AI Framework**: LangGraph, LangChain Core
- **LLM**: OpenAI (GPT-4)
- **RAG**: ChromaDB (vector database) with OpenAI embeddings
- **Guardrails**: Guardrails AI + Pydantic validation
- **Database**: PostgreSQL (asyncpg)
- **Observability**: LangSmith

## Key Features

- ✅ Structured JSON outputs from LLM
- ✅ Human-in-the-loop approval for all write actions
- ✅ RAG-based policy retrieval from ChromaDB
- ✅ Automatic looping when information is missing
- ✅ Comprehensive observability with LangSmith
- ✅ Transactional and idempotent write actions
- ✅ Strict output validation with Guardrails AI

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- LangSmith account (optional but recommended)

### Installation

1. **Clone the repository and navigate to the project directory**

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Start PostgreSQL with Docker Compose**
   ```bash
   docker-compose up -d
   ```

6. **Initialize the database**
   ```bash
   # Run database migrations (if using Alembic)
   alembic upgrade head
   ```

7. **Embed policy documents into ChromaDB**
   ```bash
   python scripts/embed_policies.py
   ```

8. **Start the FastAPI server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST /chat

Send a customer support message to the agent.

**Request:**
```json
{
  "message": "Where is my order #12345?",
  "conversation_id": "optional-conversation-id"
}
```

**Response:**
```json
{
  "response": "Your order #12345 is currently in transit...",
  "requires_approval": false,
  "approval_id": null
}
```

### POST /approvals/{approval_id}

Approve or reject a proposed action.

**Request:**
```json
{
  "status": "APPROVED"  // or "REJECTED"
}
```

**Response:**
```json
{
  "status": "approved",
  "message": "Order cancellation executed successfully"
}
```

## Project Structure

```
/app
  /api          - FastAPI routes and schemas
  /agent        - Agent orchestration logic
  /graph        - LangGraph state and nodes
  /llm          - OpenAI client wrapper
  /rag          - ChromaDB RAG implementation
  /guardrails   - Output validation
  /actions      - Write action services
  /approvals    - Human approval system
  /models       - Pydantic and SQLAlchemy models
  /observability - LangSmith tracing
  main.py       - FastAPI application entry point
/scripts        - Utility scripts (policy embedding)
/data           - Example data files
```

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Architecture Principles

1. **LLMs NEVER mutate state directly** - All write actions go through approval
2. **All write actions require human approval** - Enforced at the graph level
3. **Structured outputs only** - All LLM responses are validated JSON
4. **Fail-safe behavior** - Guardrails ensure safe fallbacks
5. **Observability first** - All steps traced in LangSmith

## License

MIT

