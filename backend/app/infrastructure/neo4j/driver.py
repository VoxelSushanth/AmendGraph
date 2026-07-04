"""
Neo4j graph database driver and repository implementation.

This module provides:
1. Neo4j driver connection management
2. Concrete implementation of the GraphRepository interface
3. All graph queries for dependency traversal
"""

from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable

from app.core.config import get_settings
from app.domain.repositories.interfaces import GraphRepository
from app.domain.models.entities import (
    DependencyGraph,
    GraphNode,
    GraphEdge,
    NodeType,
    RiskLevel,
)

settings = get_settings()

# Global driver instance
_driver: Optional[AsyncDriver] = None


def init_neo4j() -> None:
    """Initialize Neo4j driver connection."""
    global _driver

    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_pool_size=50,
    )


def get_neo4j_driver() -> AsyncDriver:
    """Get the Neo4j driver instance."""
    if _driver is None:
        init_neo4j()
    return _driver


async def close_neo4j() -> None:
    """Close Neo4j driver connection."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


class Neo4jRepository(GraphRepository):
    """
    Neo4j implementation of the GraphRepository interface.

    Provides all graph operations for the dependency engine.
    """

    def __init__(self, driver: Optional[AsyncDriver] = None):
        self.driver = driver or get_neo4j_driver()

    async def initialize_graph(self) -> bool:
        """
        Initialize the graph with default clinical trial structure.

        This creates the canonical dependency graph that represents
        how clinical trial assets relate to each other.
        """
        query = """
        // Create Endpoint nodes
        MERGE (ep1:Endpoint {
            id: 'primary_endpoint_hba1c',
            name: 'HbA1c Change from Baseline',
            type: 'Primary'
        })

        // Create Visit nodes
        MERGE (v1:Visit {id: 'week_12', name: 'Week 12', day: 84})
        MERGE (v2:Visit {id: 'week_24', name: 'Week 24', day: 168})
        MERGE (v3:Visit {id: 'baseline', name: 'Baseline', day: 0})

        // Create Population nodes
        MERGE (p1:Population {id: 'itt', name: 'Intent-to-Treat'})
        MERGE (p2:Population {id: 'pp', name: 'Per Protocol'})
        MERGE (p3:Population {id: 'safety', name: 'Safety Population'})

        // Create Dataset nodes (SDTM)
        MERGE (dm:Dataset {id: 'dm', name: 'DM', type: 'SDTM', domain: 'Demographics'})
        MERGE (lb:Dataset {id: 'lb', name: 'LB', type: 'SDTM', domain: 'Laboratory'})
        MERGE (adsl:Dataset {id: 'adsl', name: 'ADSL', type: 'ADaM', domain: 'Subject Level'})
        MERGE (adlb:Dataset {id: 'adlb', name: 'ADLB', type: 'ADaM', domain: 'Laboratory'})

        // Create Variable nodes
        MERGE (var1:Variable {id: 'hba1c', name: 'HbA1c', label: 'Hemoglobin A1c'})
        MERGE (var2:Variable {id: 'chgb', name: 'CHGB', label: 'Change from Baseline'})
        MERGE (var3:Variable {id: 'aval', name: 'AVAL', label: 'Analysis Value'})

        // Create Table nodes
        MERGE (tbl1:Table {id: 'table_14_1', name: 'Table 14.1', title: 'Primary Endpoint Analysis'})
        MERGE (tbl2:Table {id: 'table_14_2', name: 'Table 14.2', title: 'Secondary Endpoints'})

        // Create ValidationRule nodes
        MERGE (rule1:ValidationRule {id: 'rule_101', name: 'Rule 101', description: 'Check visit dates'})
        MERGE (rule2:ValidationRule {id: 'rule_104', name: 'Rule 104', description: 'Check lab values'})

        // Create DefineXML node
        MERGE (def:DefineXML {id: 'define_v2', version: '2.0', status: 'draft'})

        // Create TLF nodes
        MERGE (tlf1:TLF {id: 'tlf_001', name: 'TLF 001', type: 'Table'})
        MERGE (tlf2:TLF {id: 'tlf_002', name: 'TLF 002', type: 'Figure'})

        // Create relationships
        MERGE (ep1)-[:MEASURED_AT]->(v1)
        MERGE (ep1)-[:MEASURED_AT]->(v2)
        MERGE (ep1)-[:ANALYZED_IN_POPULATION]->(p1)

        MERGE (adlb)-[:CONTAINS_VARIABLE]->(var1)
        MERGE (adlb)-[:CONTAINS_VARIABLE]->(var2)
        MERGE (adlb)-[:CONTAINS_VARIABLE]->(var3)
        MERGE (adlb)-[:MEASURES_AT_VISIT]->(v1)
        MERGE (adlb)-[:DERIVED_FROM]->(lb)
        MERGE (adlb)-[:DERIVED_FROM]->(adsl)

        MERGE (lb)-[:CONTAINS_VARIABLE]->(var1)

        MERGE (tbl1)-[:USES_DATASET]->(adlb)
        MERGE (tbl1)-[:DISPLAYS_ENDPOINT]->(ep1)

        MERGE (rule1)-[:VALIDATES]->(adlb)
        MERGE (rule2)-[:VALIDATES]->(lb)
        MERGE (rule2)-[:CHECKS_VARIABLE]->(var1)

        MERGE (def)-[:DESCRIBES]->(adlb)
        MERGE (def)-[:DESCRIBES]->(lb)
        MERGE (def)-[:DESCRIBES]->(dm)

        MERGE (tlf1)-[:BASED_ON_TABLE]->(tbl1)
        MERGE (tlf2)-[:BASED_ON_DATASET]->(adlb)

        RETURN count(*) as created_count
        """

        async with self.driver.session() as session:
            try:
                result = await session.run(query)
                record = await result.single()
                return record is not None
            except ServiceUnavailable as e:
                print(f"Neo4j service unavailable: {e}")
                return False

    async def find_downstream_dependencies(
        self, node_id: str, max_depth: int = 10
    ) -> list[str]:
        """
        Find all nodes that depend on the given node.

        Traverses downstream following dependency relationships.
        """
        query = """
        MATCH (start {id: $node_id})
        CALL apoc.path.subgraphNodes(start, {
            relationshipFilter: '>',
            minLevel: 1,
            maxLevel: $max_depth
        }) YIELD node
        RETURN node.id as id
        """

        # Fallback without APOC
        fallback_query = """
        MATCH (start {id: $node_id})-[*1..$max_depth]->(downstream)
        RETURN DISTINCT downstream.id as id
        """

        async with self.driver.session() as session:
            try:
                result = await session.run(fallback_query, {
                    "node_id": node_id,
                    "max_depth": max_depth
                })
                records = await result.fetch(-1)
                return [record["id"] for record in records]
            except Exception as e:
                print(f"Error finding downstream dependencies: {e}")
                return []

    async def get_subgraph(
        self, node_ids: list[str], include_upstream: bool = False
    ) -> DependencyGraph:
        """Get a subgraph containing specified nodes."""
        if not node_ids:
            return DependencyGraph(nodes=[], edges=[])

        nodes_query = """
        UNWIND $node_ids AS node_id
        MATCH (n {id: node_id})
        RETURN n
        """

        edges_query = """
        UNWIND $node_ids AS node_id
        MATCH (n {id: node_id})
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.id IN $node_ids
        RETURN n.id as source, m.id as target, type(r) as relationship
        """

        async with self.driver.session() as session:
            # Get nodes
            node_result = await session.run(nodes_query, {"node_ids": node_ids})
            node_records = await node_result.fetch(-1)

            nodes = [
                GraphNode(
                    id=record["n"]["id"],
                    label=record["n"].get("name", record["n"]["id"]),
                    type=NodeType(record["n"].get("type", "Dataset")),
                    metadata=dict(record["n"]),
                )
                for record in node_records
            ]

            # Get edges
            edge_result = await session.run(edges_query, {"node_ids": node_ids})
            edge_records = await edge_result.fetch(-1)

            edges = [
                GraphEdge(
                    source=record["source"],
                    target=record["target"],
                    relationship=record["relationship"],
                )
                for record in edge_records
                if record["source"] and record["target"]
            ]

            return DependencyGraph(nodes=nodes, edges=edges)

    async def get_full_graph(self) -> DependencyGraph:
        """Get the complete dependency graph."""
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN 
            collect(DISTINCT n) as nodes,
            collect(DISTINCT {source: n.id, target: m.id, relationship: type(r)}) as edges
        """

        async with self.driver.session() as session:
            result = await session.run(query)
            record = await result.single()

            if not record:
                return DependencyGraph(nodes=[], edges=[])

            nodes = [
                GraphNode(
                    id=node["id"],
                    label=node.get("name", node["id"]),
                    type=NodeType(node.get("type", "Dataset")),
                    metadata=dict(node),
                )
                for node in record["nodes"]
            ]

            edges = [
                GraphEdge(
                    source=e["source"],
                    target=e["target"],
                    relationship=e["relationship"],
                )
                for e in record["edges"]
                if e["source"] and e["target"]
            ]

            return DependencyGraph(nodes=nodes, edges=edges)

    async def add_node(self, node_data: dict) -> bool:
        """Add a node to the graph."""
        node_type = node_data.get("type", "Generic")
        labels = ["Asset", node_type]

        properties = ", ".join([
            f"{key}: ${key}" for key in node_data.keys()
        ])

        query = f"""
        MERGE (n:{':'.join(labels)} {{id: $id}})
        SET n += {{{properties}}}
        RETURN n
        """

        async with self.driver.session() as session:
            try:
                await session.run(query, node_data)
                return True
            except Exception as e:
                print(f"Error adding node: {e}")
                return False

    async def add_relationship(
        self, source_id: str, target_id: str, relationship_type: str
    ) -> bool:
        """Add a relationship between two nodes."""
        query = """
        MATCH (source {id: $source_id})
        MATCH (target {id: $target_id})
        MERGE (source)-[r:RELATIONSHIP_TYPE]->(target)
        RETURN r
        """.replace("RELATIONSHIP_TYPE", relationship_type.upper())

        async with self.driver.session() as session:
            try:
                await session.run(
                    query,
                    source_id=source_id,
                    target_id=target_id
                )
                return True
            except Exception as e:
                print(f"Error adding relationship: {e}")
                return False

    async def get_node_by_id(self, node_id: str) -> Optional[dict]:
        """Get a node by its ID."""
        query = """
        MATCH (n {id: $node_id})
        RETURN n
        """

        async with self.driver.session() as session:
            result = await session.run(query, {"node_id": node_id})
            record = await result.single()

            if record:
                return dict(record["n"])
            return None

    async def search_nodes(
        self,
        node_type: Optional[str] = None,
        search_term: Optional[str] = None
    ) -> list[dict]:
        """Search for nodes by type or name."""
        conditions = []
        params = {}

        if node_type:
            conditions.append("label(n) CONTAINS $node_type")
            params["node_type"] = node_type

        if search_term:
            conditions.append("n.name CONTAINS $search_term OR n.id CONTAINS $search_term")
            params["search_term"] = search_term

        where_clause = " AND ".join(conditions) if conditions else "true"

        query = f"""
        MATCH (n)
        WHERE {where_clause}
        RETURN n
        LIMIT 100
        """

        async with self.driver.session() as session:
            result = await session.run(query, params)
            records = await result.fetch(-1)
            return [dict(record["n"]) for record in records]
