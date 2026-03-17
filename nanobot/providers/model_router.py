"""Model routing plugin system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ModelRouter(ABC):
    """
    Abstract base class for model routing plugins.
    
    Implementations can define custom logic to select models based on
    message content, context, or other factors.
    """

    @abstractmethod
    def select_model(
        self,
        messages: list[Dict[str, Any]],
        default_model: str,
        **kwargs
    ) -> str:
        """
        Select a model based on the given messages and context.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            default_model: The default model to use if no custom logic applies.
            **kwargs: Additional context or parameters.
            
        Returns:
            The selected model identifier.
        """
        pass


class DefaultModelRouter(ModelRouter):
    """
    Default model router that always returns the default model.
    """

    def select_model(
        self,
        messages: list[Dict[str, Any]],
        default_model: str,
        **kwargs
    ) -> str:
        return default_model


def load_model_router(router_path: Optional[str]) -> ModelRouter:
    """
    Load a model router from the specified path.
    
    Args:
        router_path: Path to the model router module.
        
    Returns:
        An instance of ModelRouter.
    """
    if not router_path:
        return DefaultModelRouter()
    
    try:
        import importlib.util
        import sys
        
        spec = importlib.util.spec_from_file_location("model_router", router_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["model_router"] = module
            spec.loader.exec_module(module)
            
            # Look for a class that inherits from ModelRouter
            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, ModelRouter) and obj != ModelRouter:
                    return obj()
    except Exception as e:
        from loguru import logger
        logger.warning(f"Failed to load model router: {e}")
    
    return DefaultModelRouter()
