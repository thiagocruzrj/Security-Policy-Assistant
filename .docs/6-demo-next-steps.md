# Demo Implementation Plan: Security Policy Assistant

## Overview

This document provides the **technical execution plan** to build the functional MVP (Minimum Viable Product) of the Security Policy Assistant. It is designed to be executed by a developer familiar with Python and Azure CLI.

**Goal:** A deployed Chat Interface where users can ask questions about uploaded PDFs and receive grounded answers with citations.

---

## Phase 1: Local Environment Setup (Day 1)

**Objective:** Get the code running locally against Azure resources.

### 1.1 Prerequisites
*   **Tools:**
    *   Python 3.11+
    *   Azure CLI (`az`)
    *   Terraform (or Bicep)
    *   Docker Desktop
    *   VS Code with Pylance
*   **Azure Subscription:** Required with `Owner` or `Contributor` access.

### 1.2 Repository Initialization
```bash
# Initialize Repo
mkdir security-policy-assistant
cd security-policy-assistant
git init
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install Dependencies
pip install fastapi uvicorn azure-identity azure-search-documents azure-storage-blob semantic-kernel openai python-multipart
pip freeze > requirements.txt
```

---

## Phase 2: Core Azure Infrastructure (Day 1-2)

**Objective:** Provision the backend services required for RAG.

### 2.1 Resource Group & Storage
```bash
az group create --name rg-sectBot-demo-eus --location eastus
az storage account create --name stsectbotdemo001 --resource-group rg-sectBot-demo-eus --sku Standard_LRS
az storage container create --name policy-docs --account-name stsectbotdemo001
```

### 2.2 Azure AI Search (Basic SKU for Semantic Ranker)
```bash
az search service create --name search-sectbot-demo --resource-group rg-sectBot-demo-eus --sku Basic
# Enable Semantic Search in the Portal -> Semantic Ranker -> Select Plan (Free/Standard)
```

### 2.3 Azure OpenAI (Model Deployment)
*   **Resource:** Create `aoai-sectbot-demo`.
*   **Deplyoments:**
    1.  **Name:** `gpt-4o` | **Model:** `gpt-4o` | **Version:** `2024-05-13`
    2.  **Name:** `text-embedding-3-small` | **Model:** `text-embedding-3-small`

---

## Phase 3: Ingestion Pipeline (Day 2-3)

**Objective:** Turn a PDF into a searchable vector index.

### 3.1 Index Creation (Python Script `scripts/create_index.py`)
*   Define schema with fields: `id`, `content`, `embedding`, `source_file`, `page_number`.
*   Configure Vector Profile: `Hnsw` algorithm, `cosine` metric.
*   Configure Semantic Configuration: Title field = `source_file`, Content field = `content`.

### 3.2 Ingestion Script (`scripts/ingest.py`)
1.  **Load PDF:** Use `pypdf` or Azure Document Intelligence SDK.
2.  **Chunk:** Split text by pages or paragraphs (overlap: 50 tokens).
3.  **Embed:** Call `text-embedding-3-small` for each chunk.
4.  **Upload:** Batch push to Azure AI Search.

**Run it:**
```bash
python scripts/ingest.py --file "./sample_policies/Information_Security_Policy.pdf"
```

---

## Phase 4: Backend API Development (Day 3-4)

**Objective:** Expose the RAG logic via a FastAPI endpoint.

### 4.1 FastAPI Structure (`api/main.py`)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    messages: list[dict]  # Chat history
    user_id: str

@app.post("/chat")
async def chat_endpoint(request: QueryRequest):
    # 1. Embed user query
    # 2. Search Index (Hybrid + Semantic Rerank)
    # 3. Construct System Prompt with retrieved chunks
    # 4. Call GPT-4o
    # 5. Return streamed response
    pass
```

### 4.2 Retrieval Logic (`api/rag.py`)
*   Implement `search_client.search()` with:
    *   `search_text`: User query
    *   `vector_queries`: User query embedding
    *   `select`: `["id", "content", "source_file"]`
    *   `top`: 5

---

## Phase 5: Frontend UI (Day 4-5)

**Objective:** A simple, clean chat interface.

### 5.1 Simple HTML/JS Client (`frontend/index.html`)
*   No complex framework needed for MVP. Use Vanilla JS + Tailwind CSS via CDN.
*   **Features:**
    *   Chat window (scrollable).
    *   Input box.
    *   "Thinking..." indicator.
    *   Citation rendering (e.g., `[Doc 1]`).

### 5.2 Hosting
*   **Backend:** Deploy via Azure Container Apps (`az containerapp up`).
*   **Frontend:** Deploy via Azure Static Web Apps (Free Tier) pointing to the `/frontend` folder in GitHub.

---

## Phase 6: Security Hardening (Day 5)

**Objective:** Apply the "Must Haves" from the architecture.

### 6.1 Managed Identity
*   Enable System Assigned Identity on the Container App.
*   Assign `Cognitive Services OpenAI User` and `Search Index Data Reader` roles.
*   Update code to use `DefaultAzureCredential()` instead of API Keys.

### 6.2 Authentication
*   Enable **App Service Authentication** (Easy Auth) on the Container App.
*   Configure Entra ID (Azure AD) provider.
*   Restrict access to "Authenticated Users Only".

---

## Phase 7: Demo Script (The "Showtime")

**Objective:** Demonstrate value effectively.

1.  **Scenario 1: General Policy Question**
    *   *User:* "What is the password policy?"
    *   *Bot:* "Passwords must be 12 chars..." (Cites `ISP-001`).
2.  **Scenario 2: Negative Test (Hallucination Check)**
    *   *User:* "How do I bake a cake?"
    *   *Bot:* "I cannot find baking instructions in the security policy."
3.  **Scenario 3: "Specific" Retrieval**
    *   *User:* "Who approves access to USB drives?"
    *   *Bot:* "The CISO must approve..." (Cites `Acceptable_Use_Policy.pdf`).

---

## Summary Checklist for Demo Day
- [ ] **Data:** At least 3 different policy PDFs ingested (Password, Remote Work, Acceptable Use).
- [ ] **Search:** Semantic Ranker is active and improving results.
- [ ] **UI:** Citations are clickable (or clearly visible).
- [ ] **Security:** No API keys are in the source code.