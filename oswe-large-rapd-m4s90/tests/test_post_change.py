import json
from pathlib import Path
import pytest

import sys
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.router_service import RouterService  # noqa: E402
from adapters.graph_loader import GraphLoader  # noqa: E402
from domain.models import RouteRequest, PlanStatus  # noqa: E402
from mocks.api.v2.mock_graph_api import MockGraphAPI  # noqa: E402

DATA_PATH = ROOT / "data" / "test_data.json"
EXPECTED_PATH = ROOT / "data" / "expected_postchange.json"


@pytest.fixture(scope="module")
def cases():
    return json.loads(DATA_PATH.read_text())


@pytest.fixture(scope="module")
def expected():
    return json.loads(EXPECTED_PATH.read_text())


@pytest.fixture(scope="module")
def service():
    return RouterService()


def _build_loader(case):
    if case.get("use_mock_api"):
        params = case.get("mock_params", {})
        api = MockGraphAPI(**params)
        return GraphLoader(api_client=api).load
    graph = case.get("graph")
    if graph:
        return GraphLoader(graph_dict=graph).load
    raise ValueError("no graph specified")


@pytest.mark.parametrize("case_name", [c["name"] for c in json.loads(DATA_PATH.read_text())])
def test_cases(service, cases, expected, case_name):
    case = next(c for c in cases if c["name"] == case_name)
    exp = expected.get(case_name, {})
    loader = _build_loader(case)
    req = RouteRequest(
        request_id=case["request_id"],
        source=case["source"],
        target=case["target"],
    )
    resp = service.route(req, loader)

    if exp.get("status") == "failure":
        assert resp.status == PlanStatus.FAILURE
        if "error_contains" in exp:
            assert exp["error_contains"].lower() in (resp.error or "").lower()
    else:
        assert resp.status == PlanStatus.SUCCESS
        if "algorithm" in exp:
            assert resp.algorithm == exp["algorithm"]
        if "path" in exp:
            assert resp.path == exp["path"]
        if "cost" in exp:
            assert resp.cost == pytest.approx(exp["cost"])
        if "retries" in exp:
            assert resp.retries == exp["retries"]
        if exp.get("idempotent"):
            # ensure idempotent hit metric incremented
            assert service.metrics.get('idempotent_hits') >= 1
