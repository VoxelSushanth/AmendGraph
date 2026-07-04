"""
Review service for generating and managing review tasks.

This service generates actionable tasks from impact analysis results (Step 8).
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.domain.models.entities import (
    ImpactAnalysisResult,
    ImpactedNode,
    NodeType,
    ReviewTask,
    RiskLevel,
)


class ReviewService:
    """
    Service for generating review tasks from impact analysis.

    Translates technical impact analysis into actionable work items.
    """

    # Task templates by node type
    TASK_TEMPLATES = {
        NodeType.ENDPOINT: {
            "task_name": "Update Primary Endpoint Definition",
            "owner_role": "Lead Statistician",
            "base_hours": 8.0,
        },
        NodeType.VISIT: {
            "task_name": "Update Visit Schedule",
            "owner_role": "Clinical Operations",
            "base_hours": 4.0,
        },
        NodeType.POPULATION: {
            "task_name": "Update Population Definitions",
            "owner_role": "Lead Statistician",
            "base_hours": 6.0,
        },
        NodeType.DATASET: {
            "task_name": "Regenerate Dataset",
            "owner_role": "Statistical Programmer",
            "base_hours": 12.0,
        },
        NodeType.VARIABLE: {
            "task_name": "Update Variable Derivations",
            "owner_role": "Statistical Programmer",
            "base_hours": 4.0,
        },
        NodeType.TABLE: {
            "task_name": "Update Table Specifications",
            "owner_role": "Medical Writer",
            "base_hours": 4.0,
        },
        NodeType.FIGURE: {
            "task_name": "Update Figure Specifications",
            "owner_role": "Medical Writer",
            "base_hours": 3.0,
        },
        NodeType.VALIDATION_RULE: {
            "task_name": "Update Validation Rules",
            "owner_role": "Data Manager",
            "base_hours": 2.0,
        },
        NodeType.DEFINE_XML: {
            "task_name": "Update Define-XML Document",
            "owner_role": "Standards Specialist",
            "base_hours": 6.0,
        },
        NodeType.TLF: {
            "task_name": "Update TLF Specifications",
            "owner_role": "Statistical Programmer",
            "base_hours": 4.0,
        },
        NodeType.CSR: {
            "task_name": "Update Clinical Study Report",
            "owner_role": "Medical Writer",
            "base_hours": 16.0,
        },
    }

    # Priority-based due date offsets (hours)
    PRIORITY_DUE_OFFSETS = {
        RiskLevel.CRITICAL: 24,
        RiskLevel.HIGH: 72,
        RiskLevel.MEDIUM: 168,  # 1 week
        RiskLevel.LOW: 336,  # 2 weeks
    }

    def generate_tasks(
        self,
        impact_result: ImpactAnalysisResult,
        assign_to_specific_user: bool = False,
    ) -> list[ReviewTask]:
        """
        Generate review tasks from impact analysis result.

        Creates one task per impacted node with appropriate priority and estimates.

        Args:
            impact_result: The impact analysis result
            assign_to_specific_user: If True, assigns to specific users; otherwise uses roles

        Returns:
            List of review tasks
        """
        tasks = []

        for i, node in enumerate(impact_result.impacted_nodes):
            task = self._create_task_for_node(node, i, impact_result.amendment_id)
            tasks.append(task)

        # Add dependency relationships between tasks
        self._link_task_dependencies(tasks)

        return tasks

    def _create_task_for_node(
        self,
        node: ImpactedNode,
        index: int,
        amendment_id: UUID,
    ) -> ReviewTask:
        """Create a review task for an impacted node."""
        template = self.TASK_TEMPLATES.get(
            node.node_type,
            {
                "task_name": f"Review {node.name}",
                "owner_role": "Reviewer",
                "base_hours": 4.0,
            },
        )

        # Customize task name based on risk level
        if node.priority == RiskLevel.CRITICAL:
            task_name = f"[CRITICAL] {template['task_name']} - {node.name}"
        elif node.priority == RiskLevel.HIGH:
            task_name = f"[HIGH] {template['task_name']} - {node.name}"
        else:
            task_name = f"{template['task_name']} - {node.name}"

        # Calculate estimated hours
        estimated_hours = max(
            node.estimated_rework_hours,
            template["base_hours"] * (node.risk_score / 100),
        )

        # Calculate due date based on priority
        due_offset = self.PRIORITY_DUE_OFFSETS.get(node.priority, 168)
        due_date = datetime.utcnow() + timedelta(hours=due_offset)

        # Generate instructions
        instructions = self._generate_task_instructions(node, template)

        return ReviewTask(
            task_name=task_name,
            owner_role=template["owner_role"],
            priority=node.priority,
            estimated_hours=round(estimated_hours, 1),
            due_date=due_date,
            related_node_ids=[node.node_id],
            instructions=instructions,
            status="open",
        )

    def _generate_task_instructions(
        self, node: ImpactedNode, template: dict
    ) -> str:
        """Generate detailed task instructions."""
        instructions = [
            f"Impact Reason: {node.reason}",
            f"Risk Score: {node.risk_score}/100",
            f"Confidence: {node.confidence:.0%}",
            "",
            "Required Actions:",
        ]

        if node.node_type == NodeType.DATASET:
            instructions.extend([
                "1. Review the protocol amendment details",
                "2. Identify affected variables and derivations",
                "3. Update SAS/R programs accordingly",
                "4. Regenerate the dataset",
                "5. Run validation checks",
                "6. Document changes in version control",
            ])
        elif node.node_type == NodeType.TABLE:
            instructions.extend([
                "1. Review updated endpoint/visit definitions",
                "2. Update table shell specifications",
                "3. Coordinate with programming team",
                "4. Update SAP references if needed",
            ])
        elif node.node_type == NodeType.DEFINE_XML:
            instructions.extend([
                "1. Review all affected datasets and variables",
                "2. Update metadata in Define-XML generator",
                "3. Regerate Define-XML document",
                "4. Run Pinnacle21 validation",
                "5. Address any new validation errors",
            ])
        else:
            instructions.extend([
                "1. Review the impact analysis",
                "2. Assess required changes",
                "3. Implement updates",
                "4. Verify changes with QC",
            ])

        if node.explanation:
            instructions.extend(["", f"Additional Context: {node.explanation}"])

        return "\n".join(instructions)

    def _link_task_dependencies(self, tasks: list[ReviewTask]) -> None:
        """
        Link tasks based on logical dependencies.

        For example, datasets must be regenerated before tables can be updated.
        """
        # Create lookup by node type
        tasks_by_type = {}
        for task in tasks:
            for node_id in task.related_node_ids:
                # Extract type from node_id prefix
                if node_id.startswith("dataset_"):
                    tasks_by_type[NodeType.DATASET] = task
                elif node_id.startswith("table_"):
                    tasks_by_type[NodeType.TABLE] = task
                elif node_id.startswith("define_"):
                    tasks_by_type[NodeType.DEFINE_XML] = task

        # Set up dependencies
        # Tables depend on datasets
        if NodeType.TABLE in tasks_by_type and NodeType.DATASET in tasks_by_type:
            table_task = tasks_by_type[NodeType.TABLE]
            dataset_task = tasks_by_type[NodeType.DATASET]
            if dataset_task.task_id:
                table_task.dependencies.append(str(dataset_task.task_id))

        # Define-XML depends on datasets
        if (
            NodeType.DEFINE_XML in tasks_by_type
            and NodeType.DATASET in tasks_by_type
        ):
            define_task = tasks_by_type[NodeType.DEFINE_XML]
            dataset_task = tasks_by_type[NodeType.DATASET]
            if dataset_task.task_id:
                define_task.dependencies.append(str(dataset_task.task_id))

    def estimate_total_effort(
        self, tasks: list[ReviewTask]
    ) -> dict[str, float]:
        """
        Estimate total effort by role.

        Returns a breakdown of hours by owner role.
        """
        effort_by_role = {}

        for task in tasks:
            role = task.owner_role
            effort_by_role[role] = (
                effort_by_role.get(role, 0.0) + task.estimated_hours
            )

        total_hours = sum(effort_by_role.values())
        effort_by_role["TOTAL"] = total_hours

        return effort_by_role

    def get_critical_path(self, tasks: list[ReviewTask]) -> list[ReviewTask]:
        """
        Identify the critical path of tasks.

        Returns tasks that must be completed in sequence.
        """
        # Sort by priority and dependencies
        critical = [t for t in tasks if t.priority == RiskLevel.CRITICAL]
        high = [t for t in tasks if t.priority == RiskLevel.HIGH]

        # Critical path includes highest priority tasks with dependencies
        return sorted(critical + high, key=lambda t: len(t.dependencies))
