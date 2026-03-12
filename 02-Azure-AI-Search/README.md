# 🔍 02-Azure-AI-Search

Welcome to the **Azure AI Search** directory. This pillar focuses on enterprise search, vector databases, information retrieval, and Retrieval-Augmented Generation (RAG).

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Foundational educational labs covering index creation, skillset definition (AI Enrichment), and basic querying syntax.
- **`azure-search-openai-demo/`**: The flagship "Chat on your data" enterprise architecture. A full-stack application (React frontend, Python backend) demonstrating a complete RAG pattern using Azure AI Search as the vector store.
- **`search-vector-samples/`**: Atomic, language-specific code samples (Python, C#, JS) demonstrating exactly how to perform pure Vector Search and Hybrid Search queries against Azure AI Search.
- **`search-multimodal-sample/`**: An advanced architecture demonstrating how to search across different modalities (text, images, and video) simultaneously using AI Search and Azure Open AI vision models.
- **`Azure-AI-Search-LangChain-Jira/`**: A customized implementation showing how to integrate Azure AI Search with LangChain to index and query Jira tickets/agile boards.

## 🚀 Getting Started

When executing code in this directory:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure AI Search requires an endpoint and an admin/query key. Navigate to the project directory you want to run (e.g., `cd azure-search-openai-demo`), duplicate `.env.example` to `.env`, and configure it securely.

## 🛠️ Development & Push Guidelines
1. **Index Management**: When pushing changes to index schemas (JSON definitions) or skillset definitions, ensure you document the necessary index rebuilds in your pull request. 
2. **Commiting**: Prefix your commits with `feat(search):`, `fix(search):`, or `docs(search):`.
3. **Pushing**: If you modify the `azure-search-openai-demo`, ensure you run their internal linting scripts before pushing your branch to the remote.
