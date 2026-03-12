# 🤖 08-Azure-AI-Bots

Welcome to the **Azure AI Bots** directory. This pillar focuses on conversational agents, bot frameworks, and complex dialog management systems.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Educational labs and baseline models utilizing the Bot Framework SDK (available in Node.js, C#, or Python based on the specific module). Covers fundamental paradigms such as Multi-turn dialog handling, State management, QnA Maker integration, and publishing bots to various Omnichannel deployment surfaces via the Azure Portal.

## 🚀 Getting Started

If working with Python bot implementations:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Bots often require an App ID, an App Password, and potentially various cognitive service endpoint URLs (e.g., LUIS or QnA components) depending on the integration. 
    In your project space, copy `.env.example` to `.env` to securely store these values.

## 🛠️ Development & Push Guidelines
1. **Local Emulator**: Bot development heavily relies on the Bot Framework Emulator. Ensure you test your bot locally, routing through the emulator (usually `http://localhost:3978/api/messages`), before committing any complex dialog architectures.
2. **Commiting**: Prefix your commits with `feat(bot):` or `fix(bot):`.
3. **Pushing**: Push your changes on a feature branch. Be exceptionally careful that your App ID and App Password from the Azure portal are never hardcoded inside `config.py` files—they must always remain managed through environment variables.
