# CodeLens 🔍
> Semantic codebase search engine - ask your GitHub repo questions in plain English.
> **Status: actively building**

## What it does
Paste a GitHub repo URL -> CodeLens indexes every function using 
AST-aware chunking -> ask questions in plain English -> get answers 
with exact file + function citations.

## Tech stack
- FastAPI backend
- tree-sitter AST chunking (Python, JS, TS)
- Ollama embeddings (mxbai-embed-large)
- pgvector similarity search
- Gemini 2.5 Flash for generation
- Railway deployment

## Features

- Query GitHub repositories in natural language
- AST-aware code chunking using tree-sitter
- Semantic code retrieval with pgvector embeddings
- Function and file-level source citations
- Automatic repository indexing and retrieval pipeline

## Architecture
```text
GitHub Repository
       ↓
AST Chunking (tree-sitter)
       ↓
Embeddings (Ollama)
       ↓
pgvector Retrieval
       ↓
Gemini Generation
       ↓
Answer + Source Citations
```

## How to run locally
\`\`\`bash
git clone https://github.com/NDeekshithaReddy/codelens
pip install -r requirements.txt
