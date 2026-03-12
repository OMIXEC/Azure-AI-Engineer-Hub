# 🎓 13-Basic-AI-Foundations

Welcome to the **Basic AI Foundations** directory. This pillar holds the educational core of Microsoft's official curriculum, serving as the absolute starting point for the AI-900 (Fundamentals) and AI-102 (Engineer) certifications.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: The earliest introductory labs covering basic Python REST calls versus SDK usage when connecting to generalized cognitive endpoints.
- **`AI-102-AIEngineer/`**: The complete, definitive source repository containing every single lab required to prepare for and pass the Microsoft AI-102 Cloud AI Engineer certification. Features 20+ atomic labs covering Text, Speech, Vision, and Search.
- **`AI-Engineer-Zero-to-Hero/`**: A curated sub-repository charting a holistic learning path and code milestones for absolute beginners ascending to cloud AI engineers.
- **`mslearn-ai-fundamentals/`**: The repository backing the AI-900 certification, focusing on conceptual capabilities (what AI can do) rather than deep code implementation (how to build it).
- **`azure-sdk-for-python/`**: Dedicated submodules exploring the lower-level structures of `azure-sdk-for-python` specifically relating to AI and inference.

## 🚀 Getting Started

When embarking on these educational Python labs:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Almost every introductory lab natively expects specific endpoint/key pairs.
    Configure your `.env` securely to avoid accidental commits during your learning phase:
    ```bash
    cp .env.example .env
    ```

## 🛠️ Development & Push Guidelines
1. **Course Accuracy**: These files closely map to official MSLearn paths. Try not to extensively modify the core `AI-102-AIEngineer/` lab structures unless fixing broken legacy SDK code, as students rely on these files mapping nicely to the online documentation.
2. **Commiting**: Prefix your commits with `feat(foundations):` or `fix(foundations):`.
3. **Pushing**: If you update the `AI-102` or `AI-900` materials to reflect new Azure SDK syntax changes (v2 to v3 migrations, for example), please thoroughly annotate the PR so instructors are aware.
