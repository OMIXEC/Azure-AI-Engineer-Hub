# 🎙️ 04-Azure-AI-Speech

Welcome to the **Azure AI Speech** directory. This pillar focuses on audio processing, voice synthesis, and real-time translation capabilities.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Hands-on educational labs for the fundamentals: Speech-to-Text (STT), Text-to-Speech (TTS) using Neural voices, and real-time Speech Translation.
- **`speech-sdk/`**: The comprehensive, advanced codebase showcasing deep integrations of the Microsoft Cognitive Services Speech SDK. This includes advanced scenarios like Speaker Recognition, asynchronous batch transcription, cross-lingual translation over WebSockets, and custom keyword recognition models.

## 🚀 Getting Started

If you are running the Python samples in this directory:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure AI Speech requires an endpoint (or specific Azure region name) and a primary key. Navigate to the project you are working on, duplicate the `.env.example` to `.env`, and configure your local environment.

## 🛠️ Development & Push Guidelines
1. **Audio Artifacts**: Do not commit large `.wav` or `.mp3` files (unless they are tiny, standardized test fixtures < 1MB). Add large audio data to `.gitignore`.
2. **Commiting**: Prefix your commits with `feat(speech):`, `fix(speech):`, or `docs(speech):` to maintain consistency.
3. **Pushing**: Test your changes natively before pushing. If you updated SDK integrations, ensure the dependency versions in your `requirements.txt` are pinned accurately before opening a Pull Request.
