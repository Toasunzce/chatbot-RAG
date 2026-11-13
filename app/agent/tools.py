import ast
import operator

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool

from app.interfaces import KnowledgeBase, WebSearcher

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _calc(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    raise ValueError("unsupported expression")


def build_tools(kb: KnowledgeBase, web: WebSearcher, top_k: int = 5) -> list[BaseTool]:
    @tool
    async def search_knowledge_base(query: str, config: RunnableConfig) -> str:
        """Search the user's uploaded documents. Use it first for any question
        that may relate to the user's files."""
        fragments = await kb.search(config["configurable"]["user_id"], query, k=top_k)
        if not fragments:
            return "Nothing found in the db."
        return "\n\n".join(f"[{f.source}]\n{f.text}" for f in fragments)

    @tool
    async def web_search(query: str) -> str:
        """Search the internet for fresh information: news, prices, current events."""
        try:
            return await web.search(query)
        except Exception as exc:
            return f"Web-search is anavailable: {exc}"

    @tool
    def calculator(expression: str) -> str:
        """Evaluate an arithmetic expression, e.g. '(15 + 27) * 3 / 4'. Supports + - * / ** %."""
        try:
            return str(_calc(ast.parse(expression, mode="eval").body))
        except Exception:
            return "Error: cannot calculate an expression."

    return [search_knowledge_base, web_search, calculator]