# Project: RAG-Powered Customer Support Bot

> Sample project writeup. Replace with your actual project details.
> Place your real project notes in: knowledge_base/projects/

## Overview

Built an end-to-end retrieval-augmented generation (RAG) system for customer support
automation. The system ingests product documentation and support history, embeds them
into a vector database, and uses an LLM to generate grounded answers.

## Technology Stack

- **Python** — core language
- **LangChain** — RAG orchestration, document loaders, chains
- **OpenAI API** — GPT-4 for generation, text-embedding-3-small for embeddings
- **ChromaDB** — local vector store for development; Pinecone for production
- **FastAPI** — REST API serving the chatbot
- **Docker** — containerization and deployment
- **AWS** — EC2 for hosting, S3 for document storage
- **PostgreSQL** — metadata storage and conversation history

## Architecture

1. **Ingestion pipeline:** PDFs and Markdown docs → text chunking → embedding → vector DB
2. **Query pipeline:** User question → embedding → top-k retrieval → context assembly → LLM → answer
3. **Caching layer:** Redis for embedding cache and conversation history
4. **Monitoring:** Custom metrics for retrieval quality, answer relevance, latency

## Key Achievements

- Reduced support ticket volume by 35% in first month
- 92% answer relevance score (human-evaluated sample)
- <1.2s average response time at p95
- Processed 500K+ support documents during ingestion

## Challenges Solved

- **Chunking strategy:** Experimented with 3 chunking approaches; paragraph-level
  with 10% overlap gave best retrieval precision
- **Hallucination reduction:** Added source citation requirement to prompts;
  fallback to "I don't know" when retrieval confidence is low
- **Scalability:** Migrated from ChromaDB to Pinecone when document count exceeded 100K

## Relevance

This project directly demonstrates:
- RAG system design and implementation
- LLM application development
- Production deployment on AWS
- Vector database experience
- Python and FastAPI expertise
