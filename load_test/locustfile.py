"""
Locust load test — RAG API
Çalıştır: locust -f locustfile.py --host http://localhost:8000
Web UI:   http://localhost:8089
"""
from locust import HttpUser, task, between

QUESTIONS = [
    "What is the relationship between SVD and PCA?",
    "How does matrix factorization work?",
    "What are eigenvalues used for in data science?",
    "Explain the concept of low-rank approximation.",
    "What is the difference between LU and QR decomposition?",
]


class ChatUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def ask_question(self):
        import random
        self.client.post(
            "/chat",
            json={"question": random.choice(QUESTIONS)},
            timeout=120,
        )

    @task(3)
    def health_check(self):
        self.client.get("/health")
