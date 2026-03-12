# 🏭 09-Azure-AI-Foundry

Welcome to the **Azure AI Foundry** (formerly referred to as Azure AI Studio) directory. This pillar is dedicated to Microsoft's next-generation cohesive platform designed for evaluating, orchestrating, and safely deploying complex generative AI solutions.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Guided foundational exercises demonstrating how to initialize an Azure AI Foundry project from code and how to orchestrate API calls locally using the newest SDKs.
- **`foundry-samples/`**: Complex orchestrations demonstrating interaction with models residing in the Azure Model Catalog (Llama 3, Mistral, etc.), showing how to hook custom foundational model deployments into standard inference pipelines beyond just Azure OpenAI endpoints.
- **`ai-hub/`**: Scripts and scaffolding covering the management and configuration of AI Hubs, establishing the structural organization of various subordinate Foundry projects.

## 🚀 Getting Started

When running Python workflows in this directory:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure AI Foundry code depends heavily on either the `AZURE_AI_PROJECT_CONNECTION_STRING` or a combination of Tenant IDs, Client IDs, and specific Endpoint URIs.
    Within your selected project directory, duplicate `.env.example` to `.env` to manage these secrets correctly.

## 🛠️ Development & Push Guidelines
1. **Azure CLI Login**: Development within Foundry often requires active Azure CLI/Entra identity contexts. Ensure `az login` works successfully before running these scripts.
2. **Commiting**: Prefix your commits with `feat(foundry):` or `fix(foundry):`.
3. **Pushing**: When pushing PRs modifying AI Hub connections or deployment logic, ensure the code cleanly handles deployment errors dynamically instead of crashing, as backend model availability can occasionally fluctuate.
