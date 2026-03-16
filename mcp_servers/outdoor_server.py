from __future__ import annotations

from server.app.services.outdoor_knowledge import OutdoorKnowledgeService

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None


outdoor_mcp = FastMCP(name="outdoor-demo-server") if FastMCP is not None else None


if outdoor_mcp is not None:
    knowledge = OutdoorKnowledgeService()

    @outdoor_mcp.tool()
    def answer_outdoor_question(question: str) -> dict:
        return {
            "question": question,
            "answer": knowledge.answer(question),
        }


    @outdoor_mcp.tool()
    def search_outdoor_knowledge(topic: str) -> dict:
        return {
            "topic": topic,
            "result": knowledge.answer(topic),
        }


if __name__ == "__main__":
    if outdoor_mcp is None:
        raise SystemExit("The mcp package is not installed.")
    outdoor_mcp.run(transport="streamable-http")

