from __future__ import annotations

from collections import OrderedDict
import logging
import os
from threading import Lock
from typing import Optional, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Try to import sentence_transformers and fastembed
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from fastembed import TextEmbedding
    HAS_FASTEMBED = True
except ImportError:
    HAS_FASTEMBED = False


def normalize_text(text: str) -> str:
    """统一的文本归一化工具，HIRD-P 层通用。"""
    if not text:
        return ""
    return text.strip().lower().replace(" ", "")


class EmbeddingService:
    """
    HIRD-P: 感知层语义向量服务。
    支持三级降级策略：FastEmbed -> SentenceTransformer -> 增强型 TF-IDF (离线)。
    """
    def __init__(self) -> None:
        self.model: Any = None
        self._model_type: Optional[str] = None  # "sentence_transformers", "fastembed", or "tfidf"
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self._embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
        self._embedding_cache_lock = Lock()
        self._embedding_cache_max_size = 256
        logging.info("EmbeddingService initialized")

    def _load_model(self) -> Any:
        if self.model is not None:
            return self.model

        # 策略 1: 初始化 TF-IDF 离线保底（极速，无网络依赖）
        try:
            self._tfidf_vectorizer = TfidfVectorizer(
                analyzer="char", ngram_range=(2, 3), max_features=512
            )
            # 扩展词库以增强离线模拟能力
            risk_corpus = [
                "转账 警察 公安 检察院 法院 涉案 洗钱 办案 冻结 安全账户 配合 调查",
                "借钱 周转 急用 手术 住院 救急 朋友 同事 帮我付 猜猜我是谁 换号",
                "验证码 屏幕共享 远程控制 录屏 安全审查 资金核验 客服 退款 理财",
                "房租 工资 还款 学费 生活费 物业 消费 转账 给",
                "投资 理财 内部消息 高额回报 老师 带单 赚钱 骗局",
            ]
            self._tfidf_vectorizer.fit(risk_corpus)
        except Exception as e:
            logging.warning(f"TF-IDF init failed: {e}")

        # 策略 2: 尝试 FastEmbed (针对 CPU 推理优化)
        if HAS_FASTEMBED:
            try:
                logging.info("Attempting FastEmbed loading (BAAI/bge-small-zh-v1.5)...")
                self.model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
                self._model_type = "fastembed"
                logging.info("Model loaded via FastEmbed")
                return self.model
            except Exception:
                logging.warning("FastEmbed unavailable, falling back...")

        # 策略 3: 尝试 SentenceTransformer (使用国内镜像)
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
                self._model_type = "sentence_transformers"
                logging.info("Model loaded via SentenceTransformer")
                return self.model
            except Exception:
                logging.warning("SentenceTransformer unavailable, falling back to TF-IDF")

        # 最终降级：TF-IDF
        self.model = self._tfidf_vectorizer
        self._model_type = "tfidf"
        logging.info("Using TF-IDF offline fallback")
        return self.model

    def _preprocess(self, text: str) -> str:
        """应用语义增强补丁（仅用于离线模式）。"""
        t = normalize_text(text)
        if self._model_type == "tfidf":
            synonyms = {
                "警察": "公安 检察院 法院 公检法 办案",
                "公安": "警察 检察院 法院 公检法 办案",
                "公检法": "警察 公安 检察院 法院 办案",
                "涉案": "洗钱 案件 调查 冻结",
                "借钱": "周转 急用 救急",
                "理财": "投资 赚钱 回报 盈利",
            }
            for key, val in synonyms.items():
                if key in t:
                    t += " " + val
        return t

    def prewarm(self) -> None:
        """在服务启动阶段完成模型与向量器预热，避免首个请求放大尾延迟。"""
        self._load_model()
        self.get_embedding("正常转账 房租 还款 安全账户 验证码 屏幕共享")

    def get_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * 512

        model = self._load_model()
        processed = self._preprocess(text)
        cache_key = f"{self._model_type}:{processed}"

        with self._embedding_cache_lock:
            cached = self._embedding_cache.get(cache_key)
            if cached is not None:
                self._embedding_cache.move_to_end(cache_key)
                return list(cached)

        if self._model_type == "sentence_transformers":
            vector = model.encode(processed, convert_to_numpy=True).tolist()
        elif self._model_type == "fastembed":
            vector = list(model.embed([processed]))[0].tolist()
        else: # tfidf
            vec = model.transform([processed]).toarray()[0]
            if len(vec) < 512:
                vec = np.pad(vec, (0, 512 - len(vec)))
            vector = vec.tolist()[:512]

        with self._embedding_cache_lock:
            self._embedding_cache[cache_key] = list(vector)
            self._embedding_cache.move_to_end(cache_key)
            while len(self._embedding_cache) > self._embedding_cache_max_size:
                self._embedding_cache.popitem(last=False)

        return list(vector)

    def batch_get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._load_model()
        processed_texts = [self._preprocess(t) for t in texts]

        if self._model_type == "sentence_transformers":
            return model.encode(processed_texts, convert_to_numpy=True).tolist()
        elif self._model_type == "fastembed":
            return [e.tolist() for e in model.embed(processed_texts)]
        else: # tfidf (vectorized)
            vecs = model.transform(processed_texts).toarray()
            results = []
            for vec in vecs:
                if len(vec) < 512:
                    vec = np.pad(vec, (0, 512 - len(vec)))
                results.append(vec.tolist()[:512])
            return results

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2:
            return 0.0
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (n1 * n2))


# 简单的模块级单例
_service = EmbeddingService()

def get_embedding_service() -> EmbeddingService:
    return _service
