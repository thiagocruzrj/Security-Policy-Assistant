# Azure AI Search Index Schema: security-policies-idx

This document defines the recommended Azure AI Search index schema for the Security Policy Assistant, optimized for policy retrieval, filtering, and security trimming.

## Index Name
- **security-policies-idx**

## Fields
| Field Name        | Type           | Capabilities                        | Description                                  |
|-------------------|----------------|-------------------------------------|----------------------------------------------|
| id                | string (key)   | Key                                 | Unique chunk/document key                    |
| policy_id         | string         | Filterable                          | Policy identifier                            |
| policy_name       | string         | Searchable, Filterable              | Name of the policy                           |
| section           | string         | Searchable, Filterable              | Section heading (e.g., Control, Exception)   |
| content           | string         | Searchable                          | Chunked policy text                          |
| contentVector     | vector         | Searchable                          | Embedding vector for semantic search         |
| source_uri        | string         | Filterable                          | Source document URI                          |
| classification    | string         | Filterable                          | internal/confidential                        |
| allowed_groups    | collection     | Filterable                          | Entra group IDs allowed to access            |
| effective_date    | date           | Filterable, Sortable                | Policy effective date                        |
| version           | string         | Filterable                          | Policy version/revision                      |
| chunk_id          | string         | Filterable                          | Unique chunk identifier                      |
| content_hash      | string         | Filterable                          | Hash for deduplication                      |
| last_indexed_at   | date           | Sortable                            | Last indexed timestamp                       |

## Retrieval
- **Hybrid search**: Combines keyword (BM25) and vector (semantic) search
- **Semantic ranker**: Optional, for improved relevance
- **Security trimming**: Filters on `classification` and `allowed_groups`

---
This schema supports secure, efficient, and relevant policy retrieval for enterprise-grade assistants.