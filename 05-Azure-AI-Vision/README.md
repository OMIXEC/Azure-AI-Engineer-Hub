# 👁️ 05-Azure-AI-Vision

Welcome to the **Azure AI Vision** directory. This pillar encompasses image analysis, spatial analysis, and optical character recognition.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Foundational, guided exercises covering core capabilities like Image Classification (Custom Vision), Object Detection, and Face API.
- **`azure-ai-vision/`**: A collection of comprehensive scripts demonstrating the newest features of the `azure-ai-vision` SDK. This directory includes deeper examples of content understanding, modern image analysis (Image Analysis 4.0), and next-generation video generation flows.
- **`mslearn-ai-vision/`**: The complete repository of the official Microsoft Learn path dedicated strictly to AI Vision, packed with pre-configured datasets and solution files for DALL-E integration, Advanced OCR, and generative AI vision scenarios.

## 🚀 Getting Started

When working with Python scripts in this folder:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure AI Vision typically requires a Computer Vision endpoint and key (and potentially a separate Custom Vision endpoint depending on the specific lab). Locate your project directory, copy `.env.example` to `.env`, and populate your Azure credentials.

## 🛠️ Development & Push Guidelines
1. **Handling Images**: Do not commit large banks of training images (`.jpg`, `.png`). If creating a new sample, ensure you use public, non-copyrighted proxy image URLs instead of local files whenever possible to keep the repo size down.
2. **Commiting**: Prefix your commits with `feat(vision):`, `fix(vision):`, or `docs(vision):`.
3. **Pushing**: Push your branch upstream, ensuring that any new code snippets relying on `azure-ai-vision` correctly map to the pinned library versions in the global `requirements.txt`.
