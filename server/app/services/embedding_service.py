from __future__ import annotations

import logging
from typing import Optional

# 本地 CPU 友好的轻量向量模型方案
# 预留给 V3.1-a: 安装 sentence-transformers, faiss-cpu, numpy
# 模型选型: BAAI/bge-small-zh-v1.5 (约 95MB)

class EmbeddingService:
    _instance: Optional[EmbeddingService] = None

    def __new__(cls) -> EmbeddingService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.model = None
        self._initialized = True
        logging.info("EmbeddingService initialized (Lazy loading enabled)")

    def get_embedding(self, text: str) -> list[float]:
        # HIRD-P: 感知层，负责将原始文本转换为向量表征。
        # 实际实现时将调用 sentence-transformers
        # 暂时返回 Mock 向量以通过 V3.1 初始集成
        return [0.0] * 384  # bge-small 维度通常为 384

    def batch_get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self.get_embedding(t) for t in texts]

def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
