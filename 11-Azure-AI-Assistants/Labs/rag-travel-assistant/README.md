# Smart Travel Buddy - RAG-Enabled Assistant

## Overview

Smart Travel Buddy is an AI-powered travel planning assistant that combines conversational AI with Retrieval-Augmented Generation (RAG) using Azure AI Assistant Playground's vector store capabilities.

## Use Case

Enterprise travel planning solution that provides:

- Personalized travel itineraries
- Destination insights and recommendations
- Document-based knowledge retrieval from travel guides
- Cost optimization and packing suggestions

## Architecture

```
User Query → Azure AI Assistant → Vector Store (Travel Docs) → Enriched Response
```

## Configuration

### Assistant Name

`Omixtravel`

### System Instructions

```
Always respond in a friendly, conversational tone like a helpful travel guide.
Provide step-by-step guidance for travel planning.
Include practical examples (itineraries, packing tips, transport info).
If a user asks about a place, always share key attractions, food, and culture.
Summarize long answers with bullet points or day-wise itineraries.
If you are unsure, suggest possible options instead of saying "I don't know."
```

### Assistant Description

Smart Travel Buddy is your AI-powered guide for planning trips, exploring destinations, and making smart travel decisions. It provides personalized itineraries, travel hacks, packing lists, cost-saving tips, and destination insights. It can also retrieve accurate knowledge from uploaded documents (vector store), such as travel guides, hotel info, or personal itineraries.

## Features

- **Vector Store Integration**: Upload travel guides, hotel information, and custom itineraries
- **Contextual Responses**: Retrieves relevant information from uploaded documents
- **Conversational Interface**: Natural language interaction for travel planning
- **Structured Output**: Day-wise itineraries and bullet-point summaries

## Example Prompts

### General Knowledge

- "What is Paris famous for?"
- "Give me a 3-day itinerary for Paris"

### Vector Store Retrieval

- "Summarize the Paris travel guide I uploaded"
- "What's the best time to visit Paris according to the guide?"

## Implementation Steps

1. Create assistant in Azure AI Foundry Assistant Playground
2. Configure system instructions and description
3. Enable vector store capability
4. Upload travel documents (PDF, DOCX, TXT)
5. Test with sample prompts

## Skills Demonstrated

- RAG implementation with Azure AI
- Vector store configuration
- Prompt engineering for travel domain
- Document retrieval and synthesis
- Conversational AI design

## Difficulty Level

**Intermediate** - Requires understanding of RAG patterns and vector stores

## Azure Services Used

- Azure OpenAI Service
- Azure AI Assistant Playground
- Vector Store (Azure AI Search backend)

## Production Considerations

- Document versioning and updates
- Response latency optimization
- Cost management for vector storage
- User session management
- Multi-language support

---

**Related Projects**: Basic Assistant, Multi-Agent Orchestration
