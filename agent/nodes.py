import ast
import asyncio
import operator
import os
import httpx
import structlog

from agent.state import AgentState
from retrieval.hybrid_searcher import hybrid_search

logger = structlog.get_logger()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")


async def _llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
        )
        response.raise_for_status()
    return response.json()["message"]["content"].strip()


# --- Planner ---

async def planner(state: AgentState) -> dict:
    """Soruyu analiz eder: hesap mı, bilgi sorusu mu? Sorguyu yeniden yazar."""
    question = state["question"]

    route_prompt = f"""Is this question a simple math calculation or a knowledge question?
Question: {question}
Reply with exactly one word: "calculator" or "retrieval" """

    route = await _llm(route_prompt)
    route = "calculator" if "calculator" in route.lower() else "retrieval"

    rewritten = question
    if route == "retrieval":
        rewrite_prompt = f"""Rewrite this question to be more specific and searchable in an academic paper about matrix methods and data science.
Original: {question}
Rewritten (one sentence only):"""
        rewritten = await _llm(rewrite_prompt)

    logger.info("planner_decision", route=route, rewritten_query=rewritten)
    return {"route": route, "rewritten_query": rewritten}


# --- Retriever (HyDE) ---

async def retriever(state: AgentState) -> dict:
    """HyDE ile hayali cevap üretir, onu embed ederek Qdrant'ta arar."""
    query = state["rewritten_query"]

    hyde_prompt = f"""Write a short academic paragraph that would answer this question about matrix methods and data science.
Question: {query}
Paragraph:"""
    hyde_doc = await _llm(hyde_prompt)

    # Hybrid search: HyDE doc ile vektör + graph birleşimi, BGE rerank
    loop = asyncio.get_event_loop()
    chunks = await loop.run_in_executor(None, hybrid_search, hyde_doc)
    logger.info("retriever_done", chunk_count=len(chunks), top_score=chunks[0]["rerank_score"] if chunks else 0)
    return {"hyde_document": hyde_doc, "chunks": chunks}


# --- Calculator ---

def _safe_eval(expr: str) -> float:
    _ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return _ops[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return _ops[type(node.op)](_eval(node.operand))
        raise ValueError(f"Desteklenmeyen ifade: {type(node)}")

    return _eval(ast.parse(expr, mode="eval").body)


async def calculator(state: AgentState) -> dict:
    """Sorudan matematiksel ifadeyi çıkarıp hesaplar."""
    question = state["question"]

    extract_prompt = f"""Extract only the mathematical expression from this question. Return only the expression, nothing else.
Question: {question}
Expression:"""
    expr = await _llm(extract_prompt)
    expr = expr.strip().split("\n")[0]

    try:
        result = _safe_eval(expr)
        answer = f"{expr} = {result}"
    except Exception:
        answer = f"Hesaplama yapılamadı: {expr}"

    logger.info("calculator_done", expression=expr, result=answer)
    return {"answer": answer, "chunks": []}


# --- Responder ---

async def responder(state: AgentState) -> dict:
    """Chunk'ları ve geçmişi kullanarak cevap üretir."""
    if state.get("answer"):
        return {"answer": state["answer"]}

    question = state["question"]
    chunks = state.get("chunks", [])
    history = state.get("history", [])

    context = "\n\n".join(c["text"] for c in chunks) if chunks else ""

    prompt = f"""Sen bir matematik asistanısın.
Aşağıdaki bağlamı kullanarak soruyu cevapla.
Bağlamda cevap yoksa "Bu bilgi belgelerimde yer almıyor." de.

Bağlam:
{context}

Soru: {question}"""

    messages = history + [{"role": "user", "content": prompt}]
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": LLM_MODEL, "messages": messages, "stream": False},
        )
        response.raise_for_status()
    answer = response.json()["message"]["content"]

    logger.info("responder_done", answer_length=len(answer))
    return {"answer": answer}


# --- Evaluator (Self-RAG) ---

async def evaluator(state: AgentState) -> dict:
    """Cevabın yeterliliğini değerlendirir."""
    question = state["question"]
    answer = state["answer"]
    retry_count = state.get("retry_count", 0)

    eval_prompt = f"""Does this answer sufficiently answer the question?
Question: {question}
Answer: {answer}
Reply with exactly one word: "yes" or "no" """

    verdict = await _llm(eval_prompt)
    is_sufficient = "yes" in verdict.lower()

    logger.info("evaluator_done", is_sufficient=is_sufficient, retry_count=retry_count)
    return {"is_sufficient": is_sufficient, "retry_count": retry_count + 1}
