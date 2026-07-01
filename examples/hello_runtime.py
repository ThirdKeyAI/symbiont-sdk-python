"""Hello, runtime — the smallest end-to-end Symbiont SDK example.

Connects to a running Symbiont runtime, checks its health, and lists the
agents it knows about.

Prerequisites:
  - A Symbiont runtime reachable at SYMBIONT_BASE_URL (default
    http://localhost:8080/api/v1). Start one with `symbi up` or the Docker
    quick-start (see the main Symbiont README).
  - Optionally SYMBIONT_API_KEY if your runtime requires authentication.

Run:
  pip install symbiont-sdk
  python examples/hello_runtime.py
"""

import os

from symbiont import Client


def main() -> None:
    client = Client(
        api_key=os.environ.get("SYMBIONT_API_KEY"),
        base_url=os.environ.get("SYMBIONT_BASE_URL", "http://localhost:8080/api/v1"),
    )

    print("health:", client.health_check())

    agent_ids = client.list_agents()
    if not agent_ids:
        print("no agents registered yet — scaffold one with `symbi init`")
        return

    for agent_id in agent_ids:
        status = client.get_agent_status(agent_id)
        print(agent_id, status.state, status.resource_usage)


if __name__ == "__main__":
    main()
