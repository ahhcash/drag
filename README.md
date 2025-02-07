# dRAG 🐉

chat with your docs using the power of RAG (retrieval augmented generation)! drop any documentation link and start asking questions in natural language.

## what it does

dRAG crawls through your documentation, chunks it up intelligently, and creates a chatbot that can answer questions about your docs with precise references. no more ctrl+f hell!

### key features

- **easy ingestion**: just drop a url, we handle the rest
- **smart crawling**: automatically detects and validates documentation sites
- **vector search**: uses state-of-the-art embeddings for accurate retrieval
- **context-aware responses**: provides answers with links to source documentation
- **multiple doc sets**: maintain separate chatbots for different documentation
- **async processing**: handles large documentation sets efficiently

## tech stack

- **backend**: fastapi + python (async all the way!)
- **vector store**: postgres + pgvector
- **embeddings**: openai
- **llm**: anthropic's claude
- **crawler**: crawlee
- **task orchestration**: prefect

## api usage

### ingest new documentation

```bash
curl -X POST http://localhost:8000/docs/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.example.com",
    "name": "example_docs",
    "max_pages": 100
  }'
```

### chat with your docs

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": {
      "id_or_name": "example_docs"
    },
    "message": "how do i get started?"
  }'
```

## how it works

1. **validation**: first checks if the url points to valid documentation
2. **crawling**: recursively crawls the documentation site, respecting rate limits
3. **processing**: converts html to text, preserving important structure
4. **chunking**: splits content into optimal chunks for retrieval
5. **embedding**: generates embeddings for semantic search
6. **storage**: saves chunks and metadata in postgres
7. **retrieval**: uses vector similarity to find relevant context
8. **generation**: combines retrieved context with claude for accurate responses

## contributing

check out CONTRIBUTING.md for development setup and guidelines!