from app.providers.model_registry import ModelRegistry


def test_registry_has_providers():
    registry = ModelRegistry()
    providers = registry.providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert "groq" in providers
    assert "gemini" in providers
