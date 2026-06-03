# CodeLens 🔍
> Semantic codebase search engine — ask your GitHub repo questions in plain English.
> **Status: actively building** (Week 2/4)

## What it does
Paste a GitHub repo URL → CodeLens indexes every function using 
AST-aware chunking → ask questions in plain English → get answers 
with exact file + function citations.

## Tech stack
- FastAPI backend
- tree-sitter AST chunking (Python, JS, TS)
- Ollama embeddings (mxbai-embed-large)
- pgvector similarity search
- Gemini 2.5 Flash for generation
- Railway deployment (coming Week 3)

## Progress
- [x] AST-aware chunker with tree-sitter
- [x] Ollama embeddings + pgvector storage
- [x] Retrieval + Gemini generation pipeline
- [x] ingest_folder() — indexes any local Python project
- [ ] FastAPI /ingest and /query endpoints
- [ ] GitHub URL ingestion
- [ ] Hybrid BM25 + semantic search
- [ ] Cross-encoder reranker
- [ ] Web UI
- [ ] Railway deployment

## How to run locally
\`\`\`bash
git clone https://github.com/yourusername/codelens
pip install -r requirements.txt
# Add your GEMINI_API_KEY to .env
uvicorn main:app --reload
\`\`\`