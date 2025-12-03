Background reconstruction — legacy `issue_project`

Summary (inferred):
- Business domain: logistics/routing — computes optimal routes in a directed weighted graph (could model shipment routing, scheduling, or path planning).
- Primary capability: compute shortest path between nodes using graph algorithms.
- Core flow: load graph (JSON), compute shortest path via `dijkstra_shortest_path`, return path and cost.
- API surface (library): Graph.from_json_file, Graph.from_edge_list, dijkstra_shortest_path.

Key assumptions and uncertainties:
- The product expects to support negative edge weights optionally (e.g., representing discounts or rebates), or must explicitly reject them; tests indicate inconsistent expectations.
- The code is packaged as a library, not a network service — unclear if it's used in a microservice or embedded (no HTTP endpoints in repo).
- No CI or deployment manifests in `issue_project` — likely a small component in a larger system.
- No telemetry or structured logging present.

Dependencies and boundaries:
- Pure Python implementation with standard library (json, heapq). No external infra or DB shown.
- Consumers likely call `dijkstra_shortest_path` synchronously; long-running graphs could cause timeouts.

Primary uncertainty to resolve with stakeholders:
- Must v2 support negative weights (Bellman-Ford) or simply validate and reject them?
- Expected performance and graph sizes (nodes/edges) — affects algorithm selection and storage (in-memory vs DB).
- Integration pattern: library vs service; if service, need API, auth, quotas and SLA.

Next step: current-state scan and root-cause analysis based on repository and tests.