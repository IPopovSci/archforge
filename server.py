from mcp.server.mcpserver import MCPServer
import harness

server = MCPServer("architecture-harness")


@server.tool()
def route_task(paths: list[str]) -> dict:
    """Choose the minimum workflow from intended paths."""
    return harness.RuleProvider().decide(paths, ["FAST", "STANDARD", "FULL"])


@server.tool()
def capability_catalog() -> dict:
    """Build the revision-bound component catalog in the current clean repository."""
    return harness.catalog().model_dump()


@server.tool()
def retrieve_context(query: str) -> list[dict]:
    """Retrieve bounded source excerpts with a revision and Trail pointer."""
    return harness.get_context(query)


@server.tool()
def compile_ticket(ticket: harness.Ticket) -> dict:
    """Compile typed intent into a content-addressed contract."""
    return harness.compile_ticket(ticket)


if __name__ == "__main__":
    server.run()
