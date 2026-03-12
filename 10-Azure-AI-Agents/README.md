# 🕵️ 10-Azure-AI-Agents

Welcome to the **Azure AI Agents** directory. This pillar explores autonomous agents, multi-agent frameworks, and advanced conversational orchestration using semantic capabilities.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Foundational educational material on setting up basic agent interactions and building robust conversational flows using agentic patterns.
- **`semantic-kernel/`**: Deep dive implementations utilizing the Microsoft Semantic Kernel framework. Contains code for defining semantic functions, native plugins, and orchestrating complex chains of thought across various LLMs.
- **`RAG-Agents-Accelerator/`**: A highly advanced, production-ready enterprise accelerator demonstrating how to build a multi-agent Retrieval-Augmented Generation ecosystem capable of autonomous research and summarization using Azure tools.
- **`agents/`**: A sandbox for isolated, singular agent scripts and tests. Includes varied agent profiles like the `movie-advisor` and `omix-travel` setups.
- **`mslearn-ai-agents/`**: The complete repository mapping to the official Microsoft Learning path for designing and developing AI Agents on Azure.

## 🚀 Getting Started

If you are running the intricate Python scripts in this folder:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Agent architectures typically require multiple endpoints (LLM, Embeddings, Memory/Search integrations).
    Navigate directly to the project you wish to run, copy `.env.example` to `.env`, and populate your access keys.

## 🛠️ Development & Push Guidelines
1. **Semantic Kernel Versions**: Semantic Kernel updates frequently. Ensure `requirements.txt` in these subfolders is kept strictly pinned. If upgrading the SK version, thoroughly test plugin integrations before pushing.
2. **Commiting**: Prefix your commits with `feat(agent):`, `fix(agent):`, or `docs(agent):`.
3. **Pushing**: Push your branch upstream, ensuring that any new custom Plugins or Skills you develop include basic markdown documentation explaining their intended input/output schemas.
