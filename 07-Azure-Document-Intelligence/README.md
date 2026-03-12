# 📄 07-Azure-Document-Intelligence

Welcome to the **Azure Document Intelligence** (formerly known as Form Recognizer) directory. This pillar focuses on automated data extraction, structure identification from documents, and parsing complex PDFs.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Step-by-step tutorials covering core Document Intelligence scenarios, such as invoking Prebuilt Models (Invoices, Receipts, W-2s) and using Layout Analysis to extract complex tables from PDFs.
- **`document-processing-samples/`**: Advanced sample architectures demonstrating how to train Custom Document Extraction Models, use the General Document Model for unclassified text, and build integration pipelines that pipe extracted layout data into downstream databases or search indexes.

## 🚀 Getting Started

If you are running Python scripts in this directory:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure Document Intelligence requires a resource endpoint and a key. Within your specific project folder, duplicate `.env.example` to `.env` to configure your environment safely.

## 🛠️ Development & Push Guidelines
1. **Test Documents**: Do not commit massive PDFs or documents containing Personally Identifiable Information (PII). Use completely anonymized, sanitized, or synthetically generated PDFs (under 5MB) for your testing fixtures.
2. **Commiting**: Prefix your commits with `feat(docintel):`, `fix(docintel):`, or `docs(docintel):`.
3. **Pushing**: Push your branch to the remote repository and create a Pull Request. Ensure that any JSON parsing logic correctly accounts for the deeply nested response structures typical of Layout APIs before requesting a review.
