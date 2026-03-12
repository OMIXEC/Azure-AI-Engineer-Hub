# Function-Calling Agents

## Overview

Production-ready Azure AI agents demonstrating function calling capabilities for real-world API integrations including weather data, stock prices, and unit conversions.

## Use Case

Personal assistant that extends LLM capabilities with external data sources and computational tools, showcasing enterprise integration patterns.

## Architecture

```
User Query → Agent → Function Detection → API Call → Response Synthesis
```

## Features

### 1. Weather Information
- Real-time weather data retrieval
- Location-based queries
- Temperature, conditions, and forecasts

### 2. Stock Price Lookup
- Current stock price queries
- Company ticker symbol resolution
- Market data integration

### 3. Unit Conversion
- Length conversions (km, miles, meters, feet)
- Weight conversions (kg, lbs, grams, ounces)
- Temperature conversions (Celsius, Fahrenheit, Kelvin)
- Configurable precision

## Function Definitions

### convert_units

```json
{
  "name": "convert_units",
  "description": "Convert a numeric value between supported units for length, weight, or temperature.",
  "parameters": {
    "type": "object",
    "properties": {
      "category": { 
        "type": "string", 
        "enum": ["length", "weight", "temperature"] 
      },
      "from_unit": { "type": "string" },
      "to_unit": { "type": "string" },
      "value": { "type": "number" },
      "precision": { 
        "type": "integer", 
        "description": "Optional rounding precision." 
      }
    },
    "required": ["category", "from_unit", "to_unit", "value"]
  }
}
```

## Configuration

### Assistant Name
`Personnel Assistant`

### System Instructions
```
You are my personnel assistant to get information on weather, stock prices, 
and unit conversions.
```

## Example Prompts

### Before Function Integration
- "What is the stock price of Apple?" → *Cannot retrieve real-time data*
- "What is the weather in Delhi?" → *Cannot access weather APIs*
- "Convert 5 kilometers to miles" → *May provide approximate calculation*

### After Function Integration
- "What is the stock price of Apple?" → *Calls stock API, returns current price*
- "Weather in Mumbai?" → *Retrieves live weather data*
- "Convert 5 kilometers to miles" → *Precise conversion: 3.10686 miles*

## Implementation Files

- `2_custom_func_agent.py` - Core agent implementation
- `3_custom_func_agent_gradio.py` - Web UI with Gradio
- `user_functions.py` - Function definitions and implementations
- `env` - Environment configuration

## Skills Demonstrated

- Function calling with Azure AI Agents
- API integration patterns
- Parameter validation and type safety
- Error handling for external services
- Gradio UI development
- Environment-based configuration

## Difficulty Level

**Intermediate** - Requires understanding of function calling, API integration, and agent orchestration

## Azure Services Used

- Azure AI Agents Service
- Azure OpenAI Service

## Production Considerations

- API rate limiting and quotas
- Error handling for failed API calls
- Caching strategies for repeated queries
- Authentication and API key management
- Response validation and sanitization
- Fallback mechanisms

## Enterprise Applications

- Customer service chatbots with live data
- Internal tools integration (CRM, ERP)
- IoT device control interfaces
- Financial data aggregation
- Multi-system orchestration

## Extension Ideas

- Add calendar integration
- Email sending capabilities
- Database query functions
- File system operations
- Third-party service integrations (Slack, Teams)

---

**Related Projects**: Multi-Agent Orchestration, Basic Assistant
