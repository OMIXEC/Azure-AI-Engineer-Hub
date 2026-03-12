# 🧠 01-Azure-OpenAI

Welcome to the **Azure OpenAI** directory. This pillar represents the core of Generative AI within the Azure ecosystem, covering Chat Completions, Embeddings, and Enterprise implementations.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Official educational labs covering the foundational usage of the Azure OpenAI SDK, including prompt engineering and basic deployments.
- **`azure-oai-proxy/`**: An enterprise-grade reverse proxy implementation for Azure OpenAI. Used for load balancing, logging, and security filtering between your apps and the foundational models.
- **`azurechatgpt/`**: A production-ready, enterprise ChatGPT clone built specifically for Azure OpenAI. It features a modern UI, chat history, and enterprise authentication.
- **`contoso-chat/`**: A sample retail copilot application (Contoso Chat) demonstrating how to build a customer service chat application using Prompt flow and Azure OpenAI.
- **`aio-openai-and-copilot/`**: A curated collection of Azure OpenAI and copilot advanced patterns and scenarios.
- **`scenarios/`**: Various advanced use-case scenarios (like structured data extraction or function calling) isolated for deep-dive learning.

## 🚀 Getting Started

If you are running the Python scripts natively:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    You will need an active Azure OpenAI endpoint and API Key. Navigate to the specific project folder you wish to run, copy the provided `.env.example` to `.env`, and fill in your endpoints:
    ```bash
    cp .env.example .env
    ```

## 🛠️ Development & Push Guidelines
1. **Local Testing**: For projects like `azure-oai-proxy` or `azurechatgpt`, ensure you test the deployment locally using the provided Dockerfiles or `npm run dev` / `python main.py` triggers before pushing.
2. **Commiting**: Prefix your commits with `feat(oai):`, `fix(oai):`, or `docs(oai):` to maintain a clean history.
3. **Pushing**: Push your feature branch and open a PR. If you modified `azurechatgpt` or the `proxy`, ensure you verify that the build steps pass locally before requesting review.
