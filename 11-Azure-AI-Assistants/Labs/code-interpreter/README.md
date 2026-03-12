# Code Interpreter Assistants

## Overview

Two specialized AI assistants demonstrating Azure AI's Code Interpreter capability for executing Python code, analyzing data, and generating visualizations in real-time.

## Projects

### 1. PyLabCoach - Python Learning Assistant

**Use Case**: Interactive Python tutoring with live code execution and visualization

**Capabilities**:
- Execute uploaded Python scripts safely
- Generate and explain visualizations
- Provide step-by-step code explanations
- Create downloadable artifacts (CSV, PNG)

**Configuration**:
```
Assistant Name: PyLabCoach

System Instructions:
You are a practical Python + data-science tutor. Your job is to run and explain 
Python code, generate visualizations, and summarize results in simple language.
When a .py file is uploaded, run it safely and show the outputs (text + saved files).
If the script generates artifacts (CSV/PNG), list them and briefly describe what each file shows.
If a user asks for modifications, edit the code and re-run it, explaining the changes.
Prefer step-by-step reasoning, and end with 2–3 key takeaways.
Important: Reply only to queries about Python, code, math, data analysis, or working 
with uploaded files. For anything else, respond: "I can only help with Python/code 
and data-related tasks."
```

**Example Prompts**:
- "What does the attached Python script do?"
- "Run customer_churn_demo.py and show all outputs"
- "Show top 10 rows of churn_data.csv and basic stats"

---

### 2. DataAnalyzerPro - Data Analysis Assistant

**Use Case**: Automated data analysis with statistical insights and visualizations

**Capabilities**:
- Automatic dataset inspection (columns, dtypes, missing values)
- Statistical analysis and correlation studies
- Chart generation (heatmaps, box plots, distributions)
- Actionable insights extraction

**Configuration**:
```
Assistant Name: DataAnalyzerPro

System Instructions:
You are a skilled data-analyst assistant. Your goal is to analyze datasets, run 
calculations, build visualizations, and summarize insights in plain English.
Work step-by-step and explain your reasoning clearly.
When helpful, create charts or tables.
If a file is uploaded, automatically inspect it (columns, dtypes, missing values) 
before analysis.
Be concise and actionable—always end with 2–3 clear takeaways.
Important: Reply only to queries about data analysis, math, statistics, programming, 
or working with uploaded files. For anything else, respond with: "I can only help 
with data analysis and code-related tasks."
```

**Example Prompts**:
- "Load student_scores.csv, show the first 5 rows, and summarize each column"
- "Build a heatmap of the correlation between subjects and explain any relationships"
- "Who are the top 5 students by overall average across all subjects?"
- "Plot a box plot for each subject and describe spread and skew"

## Architecture

```
User Upload → Code Interpreter → Python Execution → Results + Artifacts
                                        ↓
                                  Visualization
                                        ↓
                                  Natural Language
                                    Explanation
```

## Skills Demonstrated

- Code Interpreter integration
- Secure code execution in sandboxed environment
- Data analysis automation
- Visualization generation
- Domain-specific prompt engineering
- Artifact management and download

## Difficulty Level

**Intermediate** - Requires understanding of code execution capabilities and data analysis workflows

## Azure Services Used

- Azure OpenAI Service
- Azure AI Assistant Playground
- Code Interpreter (built-in capability)

## Sample Data

- `customer_churn_demo.py` - ML pipeline demonstration
- `student_scores.csv` - Educational dataset for analysis

## Production Considerations

- Code execution timeout limits
- File size restrictions
- Security sandboxing
- Artifact storage and cleanup
- Rate limiting for compute-intensive operations

## Enterprise Applications

- Automated reporting systems
- Data quality monitoring
- Educational platforms
- Business intelligence assistants
- Research data analysis

---

**Related Projects**: Customer Churn Prediction, Data Analytics
