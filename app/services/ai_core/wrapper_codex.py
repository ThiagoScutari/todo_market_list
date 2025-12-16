import os
import json  # <--- IMPORTANTE: Adicionado para converter a string da OpenAI
from typing import Any, List, Optional, Dict, Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
)
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.runnables import Runnable
from pydantic import Field
from openai import OpenAI

class GPT5CodexResponsesWrapper(BaseChatModel):
    """
    Wrapper customizado que simula o comportamento do Codex/Responses API
    usando o endpoint estável do GPT-4o para fins de validação.
    """
    
    model_name: str = Field(default="gpt-4o", alias="model") 
    reasoning_effort: str = Field(default="medium") 
    api_key: Optional[str] = Field(default=None)
    client: Any = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.client:
            self.client = OpenAI(api_key=self.api_key or os.getenv("OPENAI_API_KEY"))

    @property
    def _llm_type(self) -> str:
        return "openai-responses-api-wrapper"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        openai_messages = self._convert_messages_to_openai(messages)
        tools_payload = kwargs.get("tools", None)
        
        try:
            # Simulando o payload da nova API
            payload = {
                "model": self.model_name,
                "messages": openai_messages,
                "temperature": 0.1 # Codex precisa ser frio
            }
            
            if tools_payload:
                payload["tools"] = tools_payload

            # Chamada real ao endpoint
            response = self.client.chat.completions.create(**payload)
            
            choice = response.choices[0]
            message_content = choice.message.content
            tool_calls = choice.message.tool_calls
            
            # Montagem da resposta compatível com LangChain
            ai_message = AIMessage(
                content=message_content if message_content else "",
                tool_calls=[
                    {
                        "name": tc.function.name,
                        # CORREÇÃO CRÍTICA AQUI:
                        # O LangChain exige um DICT, mas a OpenAI devolve STR.
                        # Usamos json.loads para converter.
                        "args": json.loads(tc.function.arguments), 
                        "id": tc.id,
                        "type": "tool_call"
                    } for tc in tool_calls
                ] if tool_calls else [],
                additional_kwargs={"finish_reason": choice.finish_reason}
            )

            generation = ChatGeneration(message=ai_message)
            return ChatResult(generations=[generation])

        except Exception as e:
            # Retorna uma mensagem de erro encapsulada para não quebrar o loop
            error_msg = f"❌ Erro Crítico no Wrapper Codex: {str(e)}"
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=error_msg))])

    def _convert_messages_to_openai(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        openai_msgs = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_msgs.append({"role": "system", "content": msg.content}) 
            elif isinstance(msg, HumanMessage):
                openai_msgs.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                msg_dict = {"role": "assistant", "content": msg.content or ""}
                if msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": str(tc["args"])}
                        } for tc in msg.tool_calls
                    ]
                openai_msgs.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                openai_msgs.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content
                })
        return openai_msgs
    
    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable:
        """
        Garante a formatação correta das tools para a API da OpenAI.
        """
        from langchain_core.utils.function_calling import convert_to_openai_tool
        formatted_tools = [convert_to_openai_tool(t) for t in tools]
        return super().bind(tools=formatted_tools, **kwargs)