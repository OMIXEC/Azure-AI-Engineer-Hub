# 🗣️ 03-Azure-AI-Language

Welcome to the **Azure AI Language** directory. This pillar covers natural language processing capabilities, spanning multiple sub-services like Text Analytics and Conversational Language Understanding.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Official educational modules covering foundation NLP tasks: Sentiment Analysis, Key Phrase Extraction, Named Entity Recognition (NER), Language Translation, and Question Answering.
- **`mslearn-knowledge-mining/`**: An end-to-end knowledge mining solution utilizing Azure AI Language features (like custom NER and Text Analytics for Health) in conjunction with Azure AI Search to process and structure unorganized text data into searchable catalogs.

## 🚀 Getting Started

If working with Python scripts in this folder:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure AI Language typically requires a Language endpoint and key. Locate the specific project or lab, copy `.env.example` to `.env`, and insert your credentials.

## 🛠️ Development & Push Guidelines
1. **Model Training Data**: If you are working on Custom NER or CLU projects, do NOT commit raw, sensitive training data. Use `.gitignore` to keep datasets local, or push them to a secure Azure Storage Blob instead.
2. **Commiting**: Prefix your commits with `feat(lang):` or `fix(lang):`. 
3. **Pushing**: Push your feature branch against `main`. Ensure all unit tests (if applicable) for text extraction logic pass locally before opening a PR.
