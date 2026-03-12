# 🤝 11-Azure-AI-Assistants

Welcome to the **Azure AI Assistants** directory. This pillar is focused on task-specific assistive AI implementations primarily utilizing the structure of the Azure OpenAI Assistants API.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Step-by-step labs guiding you through the creation of your first Assistant, demonstrating how to assign instructions, equip the Assistant with tools, and run conversational Threads.

## 🚀 Getting Started

For the Python implementations in this directory:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    The Assistants API requires your Azure OpenAI endpoint and key.
    Always configure your local `.env` via the provided `.env.example` blueprint located in the lab folder.

## 🛠️ Development & Push Guidelines
1. **File Search Data**: If demonstrating the "File Search" capability of the Assistants API, ensure you only use non-sensitive, mock data (like sample manuals or generic markdown files). Do not commit proprietary documents.
2. **Commiting**: Prefix your commits with `feat(assist):` or `fix(assist):`.
3. **Pushing**: Before pushing, ensure that your scripts clean up the Assistants, Threads, and Vector Stores they dynamically create on Azure to prevent resource leaks and extra billing on the shared dev accounts.
