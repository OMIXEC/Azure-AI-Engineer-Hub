# 🎬 06-Azure-AI-Video

Welcome to the **Azure AI Video** directory. This specialized pillar focuses entirely on video analysis and the powerful Azure AI Video Indexer.

## 📂 Specific Projects
This folder contains the following implementations:
- **`Labs/`**: Guided, hands-on tutorials outlining the fundamental usage of the Azure Video Indexer API. Learn how to initiate video processing jobs, extract actionable insights (Transcripts, Faces, Topics, Keywords), and navigate video metadata.

## 🚀 Getting Started

For Python-based implementations in this folder:

1.  **Activate your Virtual Environment**:
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate`)*

2.  **Environment Variables**:
    Azure Video Indexer operations usually require an Account ID, Location region, and an API Subscription Key directly from the Video Indexer portal (sometimes distinct from standard Azure Portal keys). 
    Navigate to your immediate project folder, copy `.env.example` to `.env`, and input your keys there.

## 🛠️ Development & Push Guidelines
1. **Video Data**: Absolutely NO video files (`.mp4`, `.avi`, `.mov`) should be committed to this repository. If testing an upload snippet locally, ensure the local video path is excluded via `.gitignore` or use a publicly accessible placeholder URL.
2. **Commiting**: Prefix your commits with `feat(video):`, `fix(video):`, or `docs(video):`.
3. **Pushing**: Push your changes on a new branch. Ensure you have tested the logic thoroughly, given that video processing jobs can be asynchronous and feature long polling cycles.
