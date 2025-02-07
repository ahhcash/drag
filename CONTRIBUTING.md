# contributing to dRAG

hey! thanks for being interested in contributing to dRAG. this guide will help you get set up for development.

## development setup

### prerequisites

- python 3.12+
- postgres with pgvector extension
- supabase (optional, but recommended)

### environment setup

1. clone the repo:
```bash
git clone https://github.com/yourusername/drag.git
cd drag
```

2. create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on windows
```

3. install dependencies:
```bash
pip install -e ".[dev]"  # includes development dependencies
```

4. set up your environment variables:
```bash
cp .env.example .env
```

fill in your .env with:
```
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=your_db_name
```

### running the app locally

1. start the server:
```bash
python server.py
```

2. api will be available at `http://localhost:8000`

## development workflow

### code style

we use ruff for linting and formatting. before committing, run:
```bash
ruff check .
ruff format .
```

### type checking

we use mypy for static type checking:
```bash
mypy .
```

### testing

(coming soon!)

## project structure

```
app/
├── api/            # api routes and endpoints
├── core/           # core configuration and utilities
├── models/         # pydantic models and database schemas
└── services/       # business logic and external services
    ├── chat.py       # chat completion logic
    ├── chunker.py    # document chunking logic
    ├── crawler.py    # documentation crawling
    ├── store.py      # vector store operations
    └── validator.py  # url validation
```

## making changes

1. create a new branch for your feature/fix
2. make your changes
3. ensure all linting and type checks pass
4. submit a pull request

## roadmap & todo

- [ ] add comprehensive test suite
- [ ] add support for authentication
- [ ] implement rate limiting
- [ ] add support for pdf documentation
- [ ] improve chunking strategies
- [ ] add github actions for ci/cd

questions? feel free to open an issue!