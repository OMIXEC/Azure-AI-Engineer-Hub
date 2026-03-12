# 🛠️ 00-Custom-Projects

Welcome to the **Custom Projects** directory. This space is designed for independent, ad-hoc, or experimental Azure AI projects that don't fit perfectly into the official Microsoft Learning or Azure Samples structure. 

## 📂 Specific Projects
Currently in this directory:
- **`Labs/`**: A general sandbox area for custom, undocumented, or experimental scripts built by the engineering team on top of the Azure ecosystem. 

## 🚀 Getting Started

When working in this directory with Python-based projects, it is critically important to use an isolated environment to prevent dependency conflicts with the official labs.

1.  **Activate your Virtual Environment**:
    Always activate the repository-level virtual environment before running or installing anything locally.
    ```bash
    # From the repository root
    source venv/bin/activate
    ```
    *(Windows: `venv\Scripts\activate` or `.\venv\Scripts\Activate.ps1`)*

2.  **Environment Variables**:
    Always use a `.env` file (copied from `.env.example`) to store your local credentials securely. Ensure `.env` is never committed.

## 🛠️ Development & Push Guidelines
1. **Formatting**: Ensure your Python code adheres to PEP 8 standards. 
2. **Dependencies**: If your custom project requires new dependencies, create a localized `requirements.txt` inside your project's root (e.g., `00-Custom-Projects/My-Project/requirements.txt`).
3. **Commiting**: When committing changes inside `00-Custom-Projects`, please prefix your commit messages with `feat(custom):` or `fix(custom):`.
4. **Pushing**: Push your branch to the remote and create a Pull Request against `main`. Ensure no secrets or `.env` files are included in your PR.
