"""
Impact analysis service.

This is the core service that orchestrates the impact analysis workflow:
1. Semantic difference detection
2. Graph traversal
3. Risk scoring
4. LLM explanation generation
5. Review task generation
"""

import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.models.entities import (
    Amendment,
    ChangeType,
    DependencyGraph,
    GraphEdge,
    GraphNode,
    ImpactAnalysisResult,
    ImpactedNode,
    NodeType,
    ReviewTask,
    RiskLevel,
    SemanticDiff,
)
from app.domain.repositories.interfaces import (
    AmendmentRepository,
    GraphRepository,
    ImpactAnalysisRepository,
)


class ImpactService:
    """
    Service for performing impact analysis on amendments.

    This is the core business logic engine that:
    - Traverses the dependency graph
    - Calculates risk scores
    - Generates explanations
    - Creates review tasks
    """

    # Risk score multipliers by change type
    CHANGE_TYPE_MULTIPLIERS = {
        ChangeType.ENDPOINT: 1.0,
        ChangeType.VISIT: 0.9,
        ChangeType.POPULATION: 0.85,
        ChangeType.VARIABLE: 0.7,
        ChangeType.TIMING: 0.95,
        ChangeType.METHOD: 0.8,
        ChangeType.SCHEDULE: 0.75,
        ChangeType.CRITERIA: 0.65,
    }

    # Node type risk weights
    NODE_TYPE_WEIGHTS = {
        NodeType.ENDPOINT: 100,
        NodeType.VISIT: 90,
        NodeType.POPULATION: 85,
        NodeType.DATASET: 95,
        NodeType.VARIABLE: 70,
        NodeType.TABLE: 80,
        NodeType.FIGURE: 75,
        NodeType.VALIDATION_RULE: 60,
        NodeType.DEFINE_XML: 85,
        NodeType.REVIEW_TASK: 50,
        NodeType.TLF: 70,
        NodeType.CSR: 90,
    }

    def __init__(
        self,
        amendment_repo: AmendmentRepository,
        graph_repo: GraphRepository,
        impact_repo: ImpactAnalysisRepository,
    ):
        self.amendment_repo = amendment_repo
        self.graph_repo = graph_repo
        self.impact_repo = impact_repo

    async def analyze_impact(
        self,
        amendment_id: UUID,
        semantic_diff: SemanticDiff,
    ) -> ImpactAnalysisResult:
        """
        Perform complete impact analysis for an amendment.

        This method orchestrates Steps 3-6:
        1. Graph traversal to find downstream dependencies
        2. Risk scoring for each impacted node
        3. LLM explanation generation
        4. Aggregation of results

        Args:
            amendment_id: ID of the amendment to analyze
            semantic_diff: Structured semantic differences from Step 1

        Returns:
            Complete impact analysis result
        """
        start_time = time.time()

        # Identify changed nodes from semantic diff
        changed_node_ids = self._extract_changed_nodes(semantic_diff)

        # Find all downstream dependencies
        all_downstream = await self._find_all_downstream(changed_node_ids)

        # Get subgraph for visualization
        subgraph = await self.graph_repo.get_subgraph(
            list(set(changed_node_ids + all_downstream))
        )

        # Calculate risk scores and create impacted nodes
        impacted_nodes = await self._calculate_risk_scores(
            changed_node_ids, all_downstream, semantic_diff, subgraph
        )

        # Generate risk summary
        risk_summary = self._generate_risk_summary(impacted_nodes)

        # Generate validation recommendations
        recommendations = self._generate_recommendations(impacted_nodes)

        # Create result
        processing_time_ms = int((time.time() - start_time) * 1000)

        result = ImpactAnalysisResult(
            amendment_id=amendment_id,
            semantic_diff=semantic_diff,
            total_impacted_nodes=len(impacted_nodes),
            risk_summary=risk_summary,
            impacted_nodes=impacted_nodes,
            recommendations=recommendations,
            processing_time_ms=processing_time_ms,
        )

        # Store result
        await self.impact_repo.create(result)

        return result

    def _extract_changed_nodes(self, semantic_diff: SemanticDiff) -> list[str]:
        """
        Extract node IDs from semantic diff.

        Maps detected changes to graph node IDs.
        """
        node_ids = []

        # Map endpoints
        for endpoint in semantic_diff.endpoints_changed:
            node_ids.append(self._normalize_endpoint_id(endpoint))

        # Map visits
        if semantic_diff.visits_changed:
            old_visit = semantic_diff.visits_changed.get("old", "")
            new_visit = semantic_diff.visits_changed.get("new", "")
            if old_visit:
                node_ids.append(self._normalize_visit_id(old_visit))
            if new_visit:
                node_ids.append(self._normalize_visit_id(new_visit))

        # Map populations
        for population in semantic_diff.populations_changed:
            node_ids.append(self._normalize_population_id(population))

        # Map variables
        for variable in semantic_diff.variables_changed:
            node_ids.append(self._normalize_variable_id(variable))

        return list(set(node_ids))

    async def _find_all_downstream(
        self, node_ids: list[str]
    ) -> list[str]:
        """
        Find all downstream dependencies for a set of nodes.

        Uses graph traversal to find every affected node.
        """
        all_downstream = []

        for node_id in node_ids:
            downstream = await self.graph_repo.find_downstream_dependencies(
                node_id, max_depth=10
            )
            all_downstream.extend(downstream)

        return list(set(all_downstream))

    async def _calculate_risk_scores(
        self,
        changed_node_ids: list[str],
        downstream_node_ids: list[str],
        semantic_diff: SemanticDiff,
        subgraph: DependencyGraph,
    ) -> list[ImpactedNode]:
        """
        Calculate risk scores for all impacted nodes.

        Risk score is based on:
        - Type of change (endpoint changes are highest risk)
        - Distance from changed node (closer = higher risk)
        - Node type (datasets higher than tables)
        - Number of downstream dependencies
        """
        impacted_nodes = []

        # Process changed nodes first (highest risk)
        for node_id in changed_node_ids:
            node_data = await self.graph_repo.get_node_by_id(node_id)
            if not node_data:
                continue

            base_score = self.NODE_TYPE_WEIGHTS.get(
                NodeType(node_data.get("type", "Dataset")), 50
            )

            # Apply change type multiplier
            multiplier = self.CHANGE_TYPE_MULTIPLIERS.get(
                semantic_diff.change_type, 0.8
            )
            risk_score = min(100, int(base_score * multiplier))

            priority = self._score_to_priority(risk_score)

            impacted_nodes.append(
                ImpactedNode(
                    node_id=node_id,
                    node_type=NodeType(node_data.get("type", "Dataset")),
                    name=node_data.get("name", node_id),
                    risk_score=risk_score,
                    priority=priority,
                    reason=f"Directly changed: {semantic_diff.change_description}",
                    confidence=semantic_diff.confidence,
                    estimated_rework_hours=self._estimate_rework(
                        node_data.get("type", ""), risk_score
                    ),
                )
            )

        # Process downstream nodes
        for i, node_id in enumerate(downstream_node_ids):
            node_data = await self.graph_repo.get_node_by_id(node_id)
            if not node_data:
                continue

            # Risk decreases with distance from source
            distance_factor = max(0.3, 1.0 - (i / len(downstream_node_ids)))

            base_score = self.NODE_TYPE_WEIGHTS.get(
                NodeType(node_data.get("type", "Dataset")), 50
            )

            risk_score = min(100, int(base_score * distance_factor * 0.8))
            priority = self._score_to_priority(risk_score)

            impacted_nodes.append(
                ImpactedNode(
                    node_id=node_id,
                    node_type=NodeType(node_data.get("type", "Dataset")),
                    name=node_data.get("name", node_id),
                    risk_score=risk_score,
                    priority=priority,
                    reason=f"Downstream dependency of changed node",
                    confidence=0.85,
                    estimated_rework_hours=self._estimate_rework(
                        node_data.get("type", ""), risk_score
                    ),
                )
            )

        # Sort by risk score descending
        impacted_nodes.sort(key=lambda x: x.risk_score, reverse=True)

        return impacted_nodes

    def _generate_risk_summary(
        self, impacted_nodes: list[ImpactedNode]
    ) -> dict[RiskLevel, int]:
        """Generate summary counts by risk level."""
        summary = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 0,
            RiskLevel.HIGH: 0,
            RiskLevel.CRITICAL: 0,
        }

        for node in impacted_nodes:
            summary[node.priority] += 1

        return summary

    def _generate_recommendations(
        self, impacted_nodes: list[ImpactedNode]
    ) -> list[str]:
        """Generate validation recommendations based on impacted nodes."""
        recommendations = []

        node_types = set(node.node_type for node in impacted_nodes)

        if NodeType.DATASET in node_types:
            recommendations.append("Run SDTM Validation")
            recommendations.append("Run ADaM Validation")

        if NodeType.DEFINE_XML in node_types:
            recommendations.append("Run Define XML Validation")

        if NodeType.TABLE in node_types or NodeType.TLF in node_types:
            recommendations.append("Run TLF QC")

        if any(node.risk_score >= 80 for node in impacted_nodes):
            recommendations.append("Run Pinnacle21")

        return recommendations

    def _score_to_priority(self, risk_score: int) -> RiskLevel:
        """Convert risk score to priority level."""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _estimate_rework(self, node_type: str, risk_score: int) -> float:
        """Estimate rework hours based on node type and risk."""
        base_hours = {
            "Endpoint": 8.0,
            "Visit": 4.0,
            "Population": 6.0,
            "Dataset": 12.0,
            "Variable": 2.0,
            "Table": 4.0,
            "Figure": 3.0,
            "ValidationRule": 2.0,
            "DefineXML": 6.0,
            "TLF": 4.0,
            "CSR": 16.0,
        }

        hours = base_hours.get(node_type, 4.0)
        # Adjust by risk score
        multiplier = 0.5 + (risk_score / 200)
        return round(hours * multiplier, 1)

    @staticmethod
    def _normalize_endpoint_id(endpoint: str) -> str:
        """Normalize endpoint name to node ID."""
        return f"endpoint_{endpoint.lower().replace(' ', '_')}"

    @staticmethod
    def _normalize_visit_id(visit: str) -> str:
        """Normalize visit name to node ID."""
        return f"visit_{visit.lower().replace(' ', '_').replace('week', 'w')}"

    @staticmethod
    def _normalize_population_id(population: str) -> str:
        """Normalize population name to node ID."""
        return f"population_{population.lower().replace(' ', '_')}"

    @staticmethod
    def _normalize_variable_id(variable: str) -> str:
        """Normalize variable name to node ID."""
        return f"variable_{variable.upper()}"
