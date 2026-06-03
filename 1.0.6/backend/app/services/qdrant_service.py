from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import get_settings


class QdrantService:
    def __init__(self, collection_name: str | None = None) -> None:
        settings = get_settings()
        self.client = QdrantClient(url=settings.qdrant_url)
        # Mặc định = corpus UIT chính thức. Truyền tên khác (vd "studify_revision")
        # để dùng collection riêng, cô lập dữ liệu cá nhân.
        self.collection_name = collection_name or "studify_chunks"

    def ensure_collection(self, vector_size: int) -> None:
        collections = [item.name for item in self.client.get_collections().collections]
        if self.collection_name in collections:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )

    def upsert_chunk(self, vector: list[float], payload: dict) -> str:
        vector_id = str(uuid.uuid4())
        self.ensure_collection(len(vector))
        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[models.PointStruct(id=vector_id, vector=vector, payload=payload)],
        )
        return vector_id

    def search(
        self,
        vector: list[float],
        limit: int = 5,
        query_filter: models.Filter | None = None,
    ) -> list[models.ScoredPoint]:
        if not vector:
            return []
        try:
            result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                with_payload=True,
                query_filter=query_filter,
            )
            return result.points
        except Exception:
            return []

    def _delete_by(self, key: str, value: int) -> None:
        try:
            self.client.delete(
                collection_name=self.collection_name,
                wait=True,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key=key, match=models.MatchValue(value=value))]
                    )
                ),
            )
        except Exception:
            # collection có thể chưa tồn tại -> bỏ qua
            pass

    def delete_document_vectors(self, document_id: int) -> None:
        self._delete_by("document_id", document_id)

    def delete_notebook_vectors(self, notebook_id: int) -> None:
        self._delete_by("notebook_id", notebook_id)

