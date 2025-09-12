"""Provider type definitions."""

from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    LLMAAS = "llmaas"
    LLMAAS_DEV = "llmaas_dev"
    CUSTOM = "custom"
    GROQ = "groq"
