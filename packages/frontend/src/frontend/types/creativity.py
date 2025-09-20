"""Creativity level definitions for LLM temperature mapping."""

from enum import Enum


class CreativityLevel(str, Enum):
    """Creativity levels with corresponding temperature values."""

    NONE = "None (0.0)"
    LOW = "Low (0.2)"
    MEDIUM = "Medium (0.7)"
    MAX = "Max (1.0)"

    @property
    def temperature(self) -> float:
        """Get the temperature value for this creativity level."""
        return {
            CreativityLevel.NONE: 0.0,
            CreativityLevel.LOW: 0.2,
            CreativityLevel.MEDIUM: 0.7,
            CreativityLevel.MAX: 1.0,
        }[self]

    @classmethod
    def get_options(cls) -> list[str]:
        """Get all creativity level options as strings."""
        return [level.value for level in cls]

    @classmethod
    def from_string(cls, value: str) -> "CreativityLevel":
        """Get creativity level from string value."""
        for level in cls:
            if level.value == value:
                return level
        return cls.MEDIUM  # Default fallback
