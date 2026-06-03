from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.encode import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_container
from hestia.domain.rag.types import DenseVector, SparseVector
from tests.unit.conftest import _make_user


def _app(user=None, container=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_container] = lambda: (container or MagicMock())
    return app


class TestEncodeRouter:

    def test_dense_encode_returns_vector(self):
        container = MagicMock()
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = DenseVector(vector=[0.1, 0.2, 0.3])
        mock_encoder.default_model = "emb-model"
        container.services = {"encDense": mock_encoder}

        client = TestClient(_app(container=container))
        resp = client.post("/encode", json={"type": "dense", "input": "hello world"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "dense"
        assert len(data["vector"]) == 3

    def test_sparse_requires_collection(self):
        container = MagicMock()
        client = TestClient(_app(container=container))
        resp = client.post("/encode", json={"type": "sparse", "input": "hello"})
        assert resp.status_code == 400

    def test_sparse_with_collection_returns_vector(self):
        container = MagicMock()
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = SparseVector(indices=[0, 1], values=[0.5, 0.3])
        container.services = {"encSparse": mock_encoder}

        client = TestClient(_app(container=container))
        resp = client.post("/encode", json={"type": "sparse", "input": "hello", "collection": "my-col"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "sparse"
