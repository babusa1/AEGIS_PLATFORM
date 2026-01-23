"""
AEGIS Bedrock Module

AWS Bedrock LLM integration with mock support for local development.
"""

from aegis.bedrock.client import LLMClient, get_llm_client

__all__ = ["LLMClient", "get_llm_client"]
