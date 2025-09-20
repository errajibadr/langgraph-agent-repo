# Starting a new Langgraph Agentic Project



## Keep in mind 

- Langgraph platform uses `Postgres` & `Redis` for state management. ( only those two are supported for now if self hosting.)
- A list of python packages are already available in the langgraph platform. here [Langgraph Python Packages](https://docs.langchain.dev/langgraph/python/packages/)

## Project Structure

First Suggested arborescence: 
```
monorepo/
├── .git/
├── .github/                    # CI/CD workflows
├── docs/                       # Documentation
│   ├── api/
│   ├── deployment/
│   ├── architecture.md
│   └── README.md
├── infra/                      # Infrastructure as Code
│   ├── docker/
│   ├── kubernetes/
│   └── helm/
├── packages/                   # All Python applications & libraries
│   └── [detailed structure as discussed]
├── tests/                      # Test suites
│   ├── backend/
│   ├── frontend/
│   ├── ai-engine/
│   ├── fixtures/
│   │   ├── data/
│   │   └── mocks.py
│   ├── conftest.py
│   └── pytest.ini
├── evals/                      # Evaluation suites
│   ├── datasets/
│   ├── evals/
├── scripts/                    # Utility scripts
├── .env.example               # Environment variables template
├── .gitignore
├── .dockerignore
├── .pre-commit-config.yaml    # Git hooks configuration
├── pyproject.toml            # Workspace root configuration
├── uv.lock                   # Lockfile for all dependencies  
├── Makefile                  # Development commands
├── docker-compose.yml        # Quick development setup
├── README.md
└── LICENSE
```

Then, for the detailed structure of the packages: 


```
packages/
├── pyproject.toml              # Workspace root
├── uv.lock
├── shared/
│   ├── __init__.py
│   ├── models/                 # Domain models
│   │   ├── __init__.py
│   │   ├── entities.py
│   │   └── schemas.py
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── logging.py
│   └── utils/                  # Common utilities
│       ├── __init__.py
│       └── helpers.py
├── ai-engine/                  # LangGraph workflows
│   ├── __init__.py
│   ├── pyproject.toml
│   ├── workflows/              # LangGraph workflow definitions
│   │   ├── __init__.py
│   │   ├── rag_workflow.py
│   │   ├── agent_workflow.py
│   │   └── base.py
│   ├── agents/                 # Individual agents
│   │   ├── __init__.py
│   │   ├── research_agent.py
│   │   └── synthesis_agent.py
│   ├── tools/                  # Custom tools
│   │   ├── __init__.py
│   │   └── custom_tools.py
│   └── state/                  # State management
│       ├── __init__.py
│       └── graph_state.py
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py        # LangGraph integration endpoints
│   │   │   └── workflows.py   # Workflow management
│   │   └── dependencies.py
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── workflow_service.py
│   │   └── chat_service.py
│   └── pyproject.toml
└── frontend/
    ├── __init__.py
    ├── app.py
    ├── pages/
    │   ├── __init__.py
    │   ├── chat.py
    │   └── workflow_dashboard.py
    ├── components/
    │   ├── __init__.py
    │   └── chat_interface.py
    └── pyproject.toml
```
