from fastapi import APIRouter

router = APIRouter()

AVAILABLE_PROVIDERS = [
    {"id": "openai", "name": "OpenAI"},
    {"id": "anthropic", "name": "Anthropic"},
    {"id": "groq", "name": "Groq"},
    {"id": "gemini", "name": "Gemini"},
]

AVAILABLE_PLUGINS = [
    {"id": "mcp", "name": "MCP Tools"},
    {"id": "skills", "name": "Skills/Plugins (future)"},
]


@router.get("/")
def list_providers() -> list[dict]:
    return AVAILABLE_PROVIDERS


@router.get("/plugins")
def list_plugins() -> list[dict]:
    return AVAILABLE_PLUGINS
