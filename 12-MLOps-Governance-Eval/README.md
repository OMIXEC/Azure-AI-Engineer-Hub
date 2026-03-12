# ⚙️ 12-MLOps-Governance-Eval

Welcome to the **MLOps, Governance, and Evaluation** directory. This mission-critical pillar covers the operational side of deploying robust AI solutions, evaluating their performance, and guaranteeing responsible AI outputs.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Introductory materials around AI metric tracking, basic logging, and standard lifecycle deployments.
- **`Deploy-AI-Production/`**: Architectural documentation and scripts outlining massive-scale, high-availability deployments of AI models, usually involving Kubernetes or Azure Container Apps in frontend-backend paradigms.
- **`promptflow/`**: Deep dives into Microsoft Prompt Flow. Contains Directed Acyclic Graphs (DAGs) illustrating how to chain prompts, evaluate their outputs against baseline metrics (Groundedness, Coherence, Relevance), and deploy the resulting flows to managed endpoints.
- **`fine-tuning/`**: Code structures demonstrating how to prepare JSONL datasets and execute fine-tuning jobs on foundational models (like GPT-3.5 or `babbage`) using the Azure OpenAI SDK.
- **`mslearn-mlops/`**: The entire Microsoft Learning repository covering Machine Learning Operations on Azure (specifically tied to the older DP-100 curriculum and its modern AI integrations).

## 🚀 Getting Started

If analyzing these Python operational tools:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    These tools often require overarching Azure Service Principal credentials or comprehensive Azure ML Workspace connections.
    Initialize your configuration carefully by duplicating `.env.example` to `.env` in the target directory.

## 🛠️ Development & Push Guidelines
1. **Prompt Flow Artifacts**: When committing Prompt Flow pipelines, ensure you only commit the standard YAML definitions and the lightweight Python/Jinja node files. Exclude massive `.jsonl` evaluation caches.
2. **Commiting**: Prefix your commits with `feat(mlops):` or `fix(mlops):`.
3. **Pushing**: When pushing fine-tuning scripts, double-check that your `epochs` and `batch_size` variables aren't hardcoded to massive numbers that would rapidly exhaust testing budgets. Open a PR with detailed rationale on your governance metrics.
