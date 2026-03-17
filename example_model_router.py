"""
Example model router that selects model based on message length.

This is an example of how to create a custom model router plugin for nanobot.
"""

from nanobot.providers.model_router import ModelRouter
from typing import Any, Dict


class LengthBasedModelRouter(ModelRouter):
    """
    Model router that selects model based on the length of the user's message.
    
    - For messages with 100 characters or less: use model A
    - For messages with more than 100 characters: use model B
    """

    def select_model(
        self,
        messages: list[Dict[str, Any]],
        default_model: str,
        **kwargs
    ) -> str:
        # Find the most recent user message
        user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg
                break
        
        if not user_message:
            return default_model
        
        # Calculate message length
        content = user_message.get('content', '')
        if isinstance(content, str):
            message_length = len(content)
        elif isinstance(content, list):
            # Handle multimodal messages
            message_length = sum(len(item.get('text', '')) for item in content if isinstance(item, dict))
        else:
            message_length = 0
        
        # Select model based on message length
        if message_length <= 100:
            # Use model A for short messages
            return "gpt-4o-mini"
        else:
            # Use model B for long messages
            return "gpt-4o"
