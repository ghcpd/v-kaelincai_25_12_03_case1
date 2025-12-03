from __future__ import annotations

from fastapi import FastAPI, HTTPException
from domain.models import RouteRequest, RouteResponse
from services.router_service import RouterService
from adapters.graph_loader import GraphLoader

app = FastAPI(title="Routing Service v2")
router_service = RouterService()


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    try:
        if req.graph:
            graph_loader = lambda: req.graph  # noqa: E731
        else:
            graph_loader = GraphLoader(api_client=None, json_path="data/graph_negative_weight.json").load
        resp = router_service.route(req, graph_loader)
        if resp.status.value == "failure":
            raise HTTPException(status_code=400, detail=resp.error or "unknown error")
        return resp
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
