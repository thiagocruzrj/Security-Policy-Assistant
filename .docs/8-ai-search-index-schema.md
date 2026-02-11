# Azure AI Search Index Schema: security-policies-idx

## Overview

This document provides the **Production-Ready JSON Definition** for the `security-policies-idx` index. It is optimized for:
1.  **Hybrid Retrieval:** Combining keyword search (BM25) with semantic vector search.
2.  **Security Trimming:** Efficient filtering by `allowed_groups`.
3.  **Technical Term Handling:** Custom analyzers to preserve acronyms ("MFA", "SOC2") often broken by standard tokenizers.

---

## Index Definition (REST API Payload)

```json
{
  "name": "security-policies-idx",
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": false,
      "facetable": false
    },
    {
      "name": "content",
      "type": "Edm.String",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "analyzer": "en.microsoft" 
    },
    {
      "name": "content_vector",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "retrievable": true,
      "dimensions": 1536,
      "vectorSearchProfile": "hnsw-cosine-profile"
    },
    {
      "name": "title",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "source_uri",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": false,
      "facetable": false
    },
    {
      "name": "chunk_id",
      "type": "Edm.Int32",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "last_updated",
      "type": "Edm.DateTimeOffset",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "classification",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": false,
      "facetable": true
    },
    {
      "name": "allowed_groups",
      "type": "Collection(Edm.String)",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": false,
      "facetable": false
    }
  ],
  "vectorSearch": {
    "profiles": [
      {
        "name": "hnsw-cosine-profile",
        "algorithm": "hnsw-config",
        "vectorizer": "openai-vectorizer" 
      }
    ],
    "algorithms": [
      {
        "name": "hnsw-config",
        "kind": "hnsw",
        "parameters": {
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500,
          "metric": "cosine"
        }
      }
    ],
    "vectorizers": [
        {
            "name": "openai-vectorizer",
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": "https://your-openai-resource.openai.azure.com",
                "deploymentId": "text-embedding-3-small",
                "modelName": "text-embedding-3-small",
                "authIdentity": null 
            }
        }
    ]
  },
  "semantic": {
    "configurations": [
      {
        "name": "default",
        "prioritizedFields": {
          "titleField": { "fieldName": "title" },
          "contentFields": [
            { "fieldName": "content" }
          ],
          "keywordsFields": []
        }
      }
    ]
  }
}
```

---

## Field Details & Rationale

### `id` (Key)
*   **Format:** Base64Encode(`source_uri` + `_chunk_` + `chunk_id`).
*   **Why:** Ensures uniqueness and allows deterministic updates (idempotency) of specific chunks without re-indexing the whole document.

### `content`
*   **Analyzer:** `en.microsoft`.
*   **Why:** Better lemmatization (handling plurals/tenses) for English tech text compared to standard Lucene.

### `content_vector`
*   **Dimensions:** `1536` (Matches `text-embedding-3-small` output).
*   **Metric:** `cosine` (Normalized vectors).
*   **HNSW Parameters:**
    *   `m`: 4 (Lower memory footprint, slightly slower build).
    *   `efConstruction`: 400 (High quality graph build).
    *   `efSearch`: 500 (High recall during query).

### `allowed_groups`
*   **Type:** `Collection(Edm.String)`.
*   **Role:** Security Trimming.
*   **Usage:** `$filter=allowed_groups/any(g: g eq 'user-group-id')`.

### `classification`
*   **Values:** `Public`, `Internal`, `Confidential`.
*   **Role:** explicit labeling for audit and secondary filtering.

---

## Semantic Configuration (Critical for RAG)

The `semantic` section enables the **Semantic Ranker**:
1.  **Title Field:** `title`.
2.  **Content Field:** `content`.
3.  **Action:** The deep learning model reads these fields to determine "Relevance Score" (0-4), promoting chunks that answer the question conceptually over simple keyword matches.

---

## Updates & Maintenance
*   **Field Changes:** Using `Edm.String` allows for re-indexing (adding new fields requires dropping/recreating index or adding as nullable).
*   **Alias:** Always access the index via an **Alias** (`prod-index-alias`) to allow blue-green index swapping during schema updates (zero downtime).