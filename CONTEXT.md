# Personal RAG document assistant

The system is a single-user document assistant. It ingests personal PDF, DOCX, TXT, and Markdown documents, stores searchable chunks and OpenAI embeddings in PostgreSQL with pgvector, and answers questions with grounded citations.

Core domain terms: document, document version, document chunk, ingestion job, conversation, message, citation, indexed version, and retrieval context.
