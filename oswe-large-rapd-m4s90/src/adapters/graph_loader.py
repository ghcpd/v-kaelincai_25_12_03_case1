from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from domain.models import GraphData


class GraphLoader:
    def __init__(self, json_path: Optional[str] = None, api_client: Optional[object] = None, graph_id: Optional[str] = None, graph_dict: Optional[dict] = None):
        self.json_path = json_path
        self.api_client = api_client
        self.graph_id = graph_id
        self.graph_dict = graph_dict

    def load(self) -> GraphData:
        if self.graph_dict:
            return self._load_from_dict(self.graph_dict)
        if self.api_client:
            return self._load_from_api()
        if self.json_path:
            return self._load_from_json(self.json_path)
        raise ValueError("No graph source configured")

    def _load_from_json(self, path: str) -> GraphData:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return GraphData(**data)

    def _load_from_dict(self, data: dict) -> GraphData:
        return GraphData(**data)

    def _load_from_api(self) -> GraphData:
        assert self.api_client is not None
        gid = self.graph_id or 'default'
        return self.api_client.fetch_graph(gid)
