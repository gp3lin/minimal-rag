from typing import TypedDict


class AgentState(TypedDict):
    question: str           # kullanıcının orijinal sorusu
    rewritten_query: str    # planner'ın netleştirdiği sorgu
    route: str              # "retrieval" | "calculator"
    hyde_document: str      # HyDE için hayali cevap
    chunks: list[dict]      # Qdrant'tan gelen chunk'lar
    answer: str             # üretilen cevap
    is_sufficient: bool     # self-RAG değerlendirmesi
    retry_count: int        # kaç kez tekrar denendiği
    history: list[dict]     # konuşma geçmişi
