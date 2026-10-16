"""Text embeddings with an on-disk cache.

Every vector is stored in a small SQLite file keyed by (model, sha256(text)), so
re-indexing after a code change only pays for chunks whose text actually changed.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Protocol

import numpy as np

from copilot.config import DATA_DIR, settings

CACHE_PATH = DATA_DIR / "index" / "embedding_cache.sqlite"
OPENAI_MODEL = "text-embedding-3-small"  # 1536 dims, $0.02 / 1M tokens
BATCH_SIZE = 256


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class EmbeddingCache:
    def __init__(self, path: Path = CACHE_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS emb (model TEXT, key TEXT, vec BLOB, PRIMARY KEY (model, key))"
        )

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_many(self, model: str, texts: list[str]) -> dict[str, np.ndarray]:
        keys = [self.key(t) for t in texts]
        found = {}
        for i in range(0, len(keys), 500):
            part = keys[i : i + 500]
            rows = self.con.execute(
                f"SELECT key, vec FROM emb WHERE model = ? AND key IN ({','.join('?' * len(part))})",
                [model, *part],
            )
            found.update({k: np.frombuffer(v, dtype=np.float32) for k, v in rows})
        return found

    def put_many(self, model: str, texts: list[str], vecs: np.ndarray) -> None:
        self.con.executemany(
            "INSERT OR REPLACE INTO emb VALUES (?, ?, ?)",
            [(model, self.key(t), v.astype(np.float32).tobytes()) for t, v in zip(texts, vecs)],
        )
        self.con.commit()


class CachedEmbedder:
    """Wraps a raw embedding function with the cache; only missing texts hit the API."""

    def __init__(self, name: str, raw_embed, cache: EmbeddingCache | None = None):
        self.name = name
        self._raw = raw_embed
        self.cache = cache or EmbeddingCache()
        self.api_calls = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        cached = self.cache.get_many(self.name, texts)
        missing = list(dict.fromkeys(t for t in texts if EmbeddingCache.key(t) not in cached))
        for i in range(0, len(missing), BATCH_SIZE):
            batch = missing[i : i + BATCH_SIZE]
            vecs = np.asarray(self._raw(batch), dtype=np.float32)
            self.api_calls += 1
            self.cache.put_many(self.name, batch, vecs)
            cached.update({EmbeddingCache.key(t): v for t, v in zip(batch, vecs)})
        return np.stack([cached[EmbeddingCache.key(t)] for t in texts])


def openai_embedder() -> CachedEmbedder:
    """OpenAI or Azure OpenAI embeddings, depending on LLM_PROVIDER in .env."""
    if settings.llm_provider == "azure":
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        model = settings.azure_openai_embedding_deployment
    else:
        if not settings.openai_api_key:
            raise SystemExit("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        model = OPENAI_MODEL

    def raw(batch: list[str]) -> list[list[float]]:
        resp = client.embeddings.create(model=model, input=batch)
        return [d.embedding for d in resp.data]

    return CachedEmbedder(f"{settings.llm_provider}:{model}", raw)


class HashEmbedder:
    """Deterministic, offline 'embedding' for tests: hashed bag of words. Not semantic."""

    name = "hash-test"

    def __init__(self, dims: int = 256):
        self.dims = dims

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dims), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dims] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)
