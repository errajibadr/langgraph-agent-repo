from typing import Union

from core.config import ProviderFactory
from core.types import ProviderType
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI


def create_chat_model(provider: Union[str, ProviderType] | None = None, **kwargs) -> ChatOpenAI:
    """
    Factory function to create a ChatOpenAI instance with provider-specific configuration.

    Supported providers:
    - LLMaaS (production): Set LLM_PROVIDER=llmaas, configure with LLMAAS_* env vars
    - LLMaaS Dev (development): Set LLM_PROVIDER=llmaas_dev, configure with LLMAAS_DEV_* env vars
    - Custom: Set LLM_PROVIDER=custom, configure with {NO_PREFIX}* env vars
    - Groq: Set LLM_PROVIDER=groq, configure with GROQ_* env vars

    Environment variables:
    - LLM_PROVIDER: Provider type (llmaas, llmaas_dev, custom, groq)
    - {provider}_API_KEY: API key for the provider
    - {provider}_BASE_URL: Base URL for the provider API
    - {provider}_MODEL: Model name to use

    Args:
        provider: Provider type ('llmaas', 'llmaas_dev', 'custom', 'groq')
        **kwargs: Additional configuration to override environment variables

    Returns:
        ChatOpenAI instance configured for the specified provider

    Examples:
        # Using environment variables (recommended)
        export LLM_PROVIDER=llmaas
        export LLMAAS_API_KEY=your_api_key
        export LLMAAS_BASE_URL=https://api.llmaas.com
        export LLMAAS_MODEL=llama33-70b-instruct
        model = create_chat_model()

        # Using constructor arguments
        model = create_chat_model(
            provider="custom",
            api_key="your_key",
            base_url="https://api.example.com",
            model="gpt-5-nano"
        )

        # Using provider-specific constructor
        model = create_chat_model("llmaas_dev")

        # Create LLMaaS model
        model = create_chat_model("llmaas")

        # Create custom model with overrides
        model = create_chat_model("custom", api_key="override_key")
    """
    if isinstance(provider, str):
        provider = ProviderType(provider.lower())

    print(f"Provider: {provider}")
    # Get provider-specific settings
    provider_settings = ProviderFactory.get_provider_settings(provider)
    print(f"Provider settings: {provider_settings}")

    # Convert provider settings to dict and filter out None values
    config = {k: v for k, v in provider_settings.model_dump().items() if v is not None}

    # Override with any provided kwargs
    config.update(kwargs)

    # Handle special case: remove None top_p to avoid passing None to ChatOpenAI
    if config.get("top_p") is None:
        config.pop("top_p", None)

    return ChatOpenAI(**config)


# Backward compatibility alias - can be removed after updating all imports
CustomChatModel = create_chat_model


if __name__ == "__main__":
    from dotenv import load_dotenv
    from langchain_core.messages import HumanMessage
    from pydantic import BaseModel

    load_dotenv()

    class Summary(BaseModel):
        summary: str

    def add_tool(x: int, y: int) -> int:
        """Add two numbers"""
        return x + y

    def tool_arirthmetic(x: int, y: int) -> int:
        """Multiply two numbers"""
        return x * y

    model = create_chat_model(provider=ProviderType.GROQ, model="qwen/qwen3-32b").bind_tools(
        [add_tool, tool_arirthmetic]
    )

    message = "Always use available tools. What is 2 + 2 then multiply by 3"
    for chunk in model.stream([HumanMessage(message)]):
        if isinstance(chunk, AIMessage) and chunk.tool_calls:
            print(chunk.tool_calls)
        else:
            print(chunk.content)

    # result = create_chat_model().with_structured_output(Summary).invoke([HumanMessage("What is the weather in Tokyo?")])

    # from langchain_google_vertexai.chat_models import ChatVertexAI

    # result = ChatVertexAI(model_name="gemini-2.5-flash", location="europe-west9", project="sandbox-467809").invoke(
    #     [HumanMessage("What is the weather in Tokyo?")]
    # )
    # print(result)
