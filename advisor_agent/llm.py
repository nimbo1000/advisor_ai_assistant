import os
from langchain_community.chat_models import ChatOpenAI  # Use ChatOpenAI for chat models
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import AIMessage
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class DummyLLM(BaseLanguageModel):
    def _call(self, prompt, stop=None):
        return "[LLM] This is a dummy response."

    @property
    def _llm_type(self):
        return "dummy"

    def generate(self, messages, **kwargs):
        return [AIMessage(content="[LLM] This is a dummy response.")]

def get_llm():
    # if OPENAI_API_KEY:
    #     return ChatOpenAI(
    #         openai_api_key=OPENAI_API_KEY,
    #         model_name="gpt-4o-mini",
    #         temperature=0.2,
    #     )
    if DEEPSEEK_API_KEY:
        return ChatOpenAI(
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com/v1",
            model_name="deepseek-chat",
            temperature=0.2,
        )
    return DummyLLM() 