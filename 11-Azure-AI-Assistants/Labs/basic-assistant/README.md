# Basic Assistant - Getting Started

## Overview

Foundational Azure AI Assistant implementation demonstrating core conversational AI capabilities and best practices for prompt engineering.

## Use Case

Entry-level assistant showcasing fundamental Azure AI Foundry Assistant Playground features including system instructions, conversation management, and domain-specific responses.

## Featured Assistant: KiddoTutor

### Description
A playful educational tutor that makes learning exciting for kids by teaching math, science, language, and general knowledge in a fun, interactive way.

### Configuration

**Assistant Name**: `KiddoTutor`

**System Instructions**:
```
You are a fun and friendly teacher for kids. Use simple language, emojis, and 
stories to explain concepts. Make learning interactive with questions, rhymes, 
and quizzes. Keep tone playful and supportive.

Important: Reply only when the user's query is about kids learning, teaching, 
quizzes, rhymes, or fun knowledge. For all other topics, politely say: 
"I can only help with kids' learning."
```

**Assistant Description**:
```
A playful tutor that makes learning exciting for kids by teaching math, science, 
language, and general knowledge in a fun way.
```

## Example Prompts

### On-Topic (Successful)
- "Tell me a rhyme to learn the days of the week"
- "Create a quiz for 5th grade HISTORY"
- "Explain photosynthesis in simple words"
- "Help me with multiplication tables"

### Off-Topic (Boundary Testing)
- "Write me a business plan for a startup" → *Politely declines*

## Key Features

- **Domain Restriction**: Demonstrates scope limiting for focused assistants
- **Tone Consistency**: Maintains playful, supportive voice
- **Interactive Learning**: Uses questions, rhymes, and quizzes
- **Age-Appropriate Language**: Simple explanations with emojis

## Implementation Steps

1. Navigate to Azure AI Foundry Portal
2. Open Assistant Playground
3. Create new assistant with name "KiddoTutor"
4. Configure system instructions
5. Add assistant description
6. Test with sample prompts
7. Refine based on responses

## Skills Demonstrated

- Prompt engineering fundamentals
- System instruction design
- Domain-specific AI assistants
- Conversation boundary management
- Tone and personality configuration

## Difficulty Level

**Beginner** - Perfect starting point for Azure AI Assistant development

## Azure Services Used

- Azure AI Foundry
- Azure OpenAI Service
- Assistant Playground

## Files

- `1_create_agent.py` - Programmatic assistant creation
- `data.txt` - Sample knowledge base
- `env` - Environment configuration template

## Production Considerations

- Clear domain boundaries prevent misuse
- Consistent tone maintains user trust
- Age-appropriate content filtering
- Response length optimization for target audience
- Multi-turn conversation handling

## Extension Ideas

- Add progress tracking
- Implement difficulty levels
- Include parent/teacher dashboard
- Gamification with points and badges
- Multi-language support

## Learning Path

1. **Start Here**: Understand basic assistant configuration
2. **Next**: Explore function calling in `function-calling-agents`
3. **Advanced**: Build multi-agent systems in `multi-agent-orchestration`

---

**Related Projects**: Function-Calling Agents, RAG Travel Assistant
