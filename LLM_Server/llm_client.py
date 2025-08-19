from openai import OpenAI
from typing import List, Dict, Any, Optional
import logging

# A default logger if no specific logger is provided
default_logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the LLM client with OpenRouter configuration.
        
        Args:
            logger (logging.Logger, optional): A logger instance for logging LLM calls. 
                                               Defaults to a default logger.
        """
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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"
        )
        self.logger = logger or default_logger
        
        # Default models for different types of requests
        self.text_model = "deepseek/deepseek-r1-0528:free"
        self.vision_model = "moonshotai/kimi-vl-a3b-thinking:free"
    
    def call_text_llm(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make a text-only LLM call.
        """
        if model is None:
            model = self.text_model
            
        messages = [{"role": "user", "content": prompt}]
        
        completion_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens
        
        try:
            self.logger.debug(f"LLM Call Request:\nModel: {model}\nPrompt: {prompt[:500]}...")
            completion = self.client.chat.completions.create(**completion_params)
            response_content = completion.choices[0].message.content
            self.logger.debug(f"LLM Call Response:\n{response_content[:500]}...")
            return response_content
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return f"Error: {str(e)}"
    
    def call_vision_llm(
        self, 
        text_prompt: str, 
        image_url: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make an LLM call with both text and image.
        """
        if model is None:
            model = self.vision_model
            
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
        
        completion_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens
        
        try:
            self.logger.debug(f"Vision LLM Call Request:\nModel: {model}\nPrompt: {text_prompt[:500]}...")
            completion = self.client.chat.completions.create(**completion_params)
            response_content = completion.choices[0].message.content
            self.logger.debug(f"Vision LLM Call Response:\n{response_content[:500]}...")
            return response_content
        except Exception as e:
            self.logger.error(f"Vision LLM call failed: {e}")
            return f"Error: {str(e)}"
    
    def call_llm_with_conversation(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make an LLM call with a conversation history.
        """
        if model is None:
            model = self.text_model
            
        completion_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens
        
        try:
            self.logger.debug(f"Conversation LLM Call Request:\nModel: {model}\nMessages: {messages}")
            completion = self.client.chat.completions.create(**completion_params)
            response_content = completion.choices[0].message.content
            self.logger.debug(f"Conversation LLM Call Response:\n{response_content[:500]}...")
            return response_content
        except Exception as e:
            self.logger.error(f"Conversation LLM call failed: {e}")
            return f"Error: {str(e)}"