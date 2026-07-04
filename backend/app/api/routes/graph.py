"""
Graph routes.

Handles dependency graph visualization and exploration.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.responses import DependencyGraphResponse
from app.infrastructure.neo4j.driver import Neo4jRepository

router = APIRouter()


@router.get("/", response_model=DependencyGraphResponse)
async def get_full_graph():
    """
    Get the complete dependency graph.

    Returns all nodes and edges for React Flow visualization.
    """
    repo = Neo4jRepository()
    graph = await repo.get_full_graph()

    return DependencyGraphResponse(
        nodes=graph.nodes,
        edges=graph.edges,
        metadata={"total_nodes": len(graph.nodes), "total_edges": len(graph.edges)},
    )


@router.get("/{amendment_id}", response_model=DependencyGraphResponse)
async def get_impact_graph(amendment_id: str):
    """
    Get dependency graph filtered to impacted nodes.

    Shows only nodes affected by the amendment and their relationships.
    """
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    # For MVP, return full graph
    # In production, filter based on impact analysis results
    repo = Neo4jRepository()
    graph = await repo.get_full_graph()

    return DependencyGraphResponse(
        nodes=graph.nodes,
        edges=graph.edges,
        metadata={
            "amendment_id": str(uuid_id),
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
        },
    )


@router.get("/node/{node_id}")
async def get_node_details(node_id: str):
    """Get details for a specific node."""
    repo = Neo4jRepository()
    node = await repo.get_node_by_id(node_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found",
        )

    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "type": node.get("type"),
        "metadata": node,
    }


@router.get("/search")
async def search_nodes(
    node_type: str | None = None,
    search_term: str | None = None,
):
    """Search for nodes by type or name."""
    repo = Neo4jRepository()
    nodes = await repo.search_nodes(node_type=node_type, search_term=search_term)

    return {"nodes": nodes, "total": len(nodes)}
