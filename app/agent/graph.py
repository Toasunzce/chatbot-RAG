from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


# TODO: replace SYSTEM_PROMPT


SYSTEM_PROMPT = SystemMessage(
    "Ты — AI-ассистент. Отвечай на русском, если не попросили иначе. "
    "Если вопрос может относиться к документам пользователя, сначала вызови search_knowledge_base. "
    "Для актуальной информации используй web_search (если он тебе доступен). "
    "Любую арифметику делай через calculator. "
    "Не выдумывай факты и указывай источник в формате [файл]."
)


def build_agent(llm: BaseChatModel, tools: list[BaseTool], max_history: int = 20):
    """ReAct-агент: agent → (tools → agent)* → END. LLM и инструменты передаются снаружи."""
    base_tools = [t for t in tools if t.name != "web_search"]
    llm_base = llm.bind_tools(base_tools)
    llm_web = llm.bind_tools(tools)

    async def agent_node(state: MessagesState, config: dict):
        web_on = config["configurable"].get("web", False)
        history = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=len,
            max_tokens=max_history,
            start_on="human",
        )
        response = await (llm_web if web_on else llm_base).ainvoke([SYSTEM_PROMPT, *history])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=MemorySaver())