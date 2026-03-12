# 🏆 Azure AI Engineering Hub: The Ultimate Unified Catalog

Welcome to the **Azure AI Engineering Hub**, a highly structured, comprehensive, all-in-one repository designed for modern Cloud AI Engineers. This hub centralizes official labs, production-grade samples, and advanced orchestration patterns into a definitive service-based hierarchy.

## 🙏 Credits & Attribution
This repository serves as a centralized gateway to the Microsoft AI ecosystem. We give **full credit and special thanks** to the **Microsoft Learning (MSLearn)** and **Azure Samples** teams. 

Most of the fundamental labs and SDK demonstrations in this hub are sourced from:
- [Microsoft Learning (MSLearn)](https://github.com/MicrosoftLearning)
- [Azure Samples Official](https://github.com/Azure-Samples)

---

## 🏗️ The 13-Pillar Service Hierarchy
To ensure a smooth development experience, every Azure AI service is separated into its own definitive pillar:

### Core AI Services
1.  **`01-Azure-OpenAI`**: The heart of Generative AI. Chat completions, DALL-E, embeddings, and enterprise-grade proxies.
2.  **`02-Azure-AI-Search`**: Advanced Vector Search, Hybrid Search, and RAG patterns with LangChain.
3.  **`03-Azure-AI-Language`**: NLP, Conversational Language Understanding (CLU), and Text Analytics.
4.  **`04-Azure-AI-Speech`**: Speech-to-Text (STT), Text-to-Speech (TTS), and real-time Speech Translation.
5.  **`05-Azure-AI-Vision`**: Image classification, Object detection, and OCR.
6.  **`06-Azure-AI-Video`**: Specialized folder for **Azure AI Video Indexer** and video analysis.
7.  **`07-Azure-Document-Intelligence`**: Automated form extraction, PDF layout analysis, and document AI.

### Conversational & Agentic AI
8.  **`08-Azure-AI-Bots`**: Bot Framework, Bot Composer, and conversational design patterns.
9.  **`09-Azure-AI-Foundry`**: The new **Azure AI Foundry** (formerly Studio) SDKs and Model Catalog integration.
10. **`10-Azure-AI-Agents`**: Advanced orchestration with **Semantic Kernel**, RAG-Agents-Accelerator, and multi-agent systems.
11. **`11-Azure-AI-Assistants`**: Task-specific AI assistant implementations.

### Management & Deployment
12. **`12-MLOps-Governance-Eval`**: Production monitoring, Fine-tuning, Prompt Flow, and AI model evaluation.
13. **`13-Basic-AI-Foundations`**: Core concepts, AI-900 (Fundamentals), and the AI-102 (Engineer) certification base.

---

## 🛠️ Getting Started for Engineers

### 1. Refresh the Catalog
If you need to re-sync or clone missing repositories, run the master setup script:
```bash
./setup_azure_ai_repos.sh
```

### 2. Install Dependencies
This project provides a recursive installer that discovers and installs all `requirements.txt` files across all pillars:
```bash
python3 install_all_requirements.py --install
```

### 3. Configure Environments
Use the provided `.env.template` in the root to set your global Azure credentials and endpoint values. Each lab folder also contains `.env.example` files for localized settings.

---

## 📦 Unified Resources
This hub is the **only repo you need** to master Azure AI. It contains:
- **All Docs**: Service-specific documentation links and READMEs.
- **All Labs**: 24+ official Microsoft certification labs.
- **All Code**: 27+ advanced engineering repositories from the Azure ecosystem.

---
*Created for Azure AI Engineers & Cloud Developers.*
