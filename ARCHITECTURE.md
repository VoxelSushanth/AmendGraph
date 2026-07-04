# Protocol Amendment Dependency Graph Engine - Architecture

## Executive Summary

This document describes the architecture of a production-grade MVP for analyzing clinical protocol amendments and identifying downstream impact across clinical trial assets. The system follows Clean Architecture principles with clear separation of concerns, dependency injection, and repository patterns.

---

## 1. System Overview

### 1.1 Core Problem

Clinical protocol amendments (e.g., changing a primary endpoint from Week 12 to Week 24) have cascading effects on:
- Visit schedules
- SDTM/ADaM datasets
- Define-XML documents
- TLF specifications
- Validation rules
- Review workflows

Currently, identifying these dependencies is manual, error-prone, and expensive.

### 1.2 Solution Approach

We build a **graph-based dependency engine** where:
1. Clinical trial assets are modeled as nodes in a property graph
2. Relationships between assets are explicitly defined edges
3. When an amendment occurs, we traverse the graph to find all affected nodes
4. A risk engine scores each impacted node
5. An LLM layer provides human-readable explanations (but does NOT determine dependencies)

---

## 2. Architectural Principles

### 2.1 Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Graph Database (Neo4j)** | Dependencies are inherently graph-shaped. Relational databases require expensive JOINs for deep traversals. Neo4j provides native graph traversal with millisecond latency. |
| **LLM for Explanation Only** | LLMs are non-deterministic. Dependencies must be deterministic and auditable. The graph stores truth; LLM only translates to natural language. |
| **Event-Driven Processing** | Amendment analysis is async. Celery workers handle heavy lifting without blocking API responses. |
| **Repository Pattern** | Decouples domain logic from infrastructure. Enables swapping Neo4j for NetworkX if needed. |
| **Pydantic Models** | Single source of truth for data schemas. Shared between API validation and domain models. |

### 2.2 Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  React + TypeScript + React Flow + TanStack Query            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                               │
│  FastAPI REST Endpoints + JWT Auth + OpenAPI Docs           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  Use Cases / Services + CQRS + Event Handlers               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     DOMAIN LAYER                             │
│  Entities + Value Objects + Domain Services                 │
│  (Pure business logic, no infrastructure dependencies)      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                        │
│  Neo4j Repository + Postgres + Redis + Celery + S3          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

### 3.1 Backend Components

```
backend/
├── app/
│   ├── api/                    # HTTP Layer
│   │   ├── routes/             # API endpoints
│   │   ├── middleware/         # Auth, logging, CORS
│   │   └── schemas/            # Request/Response Pydantic models
│   │
│   ├── core/                   # Application Core
│   │   ├── config.py           # Environment configuration
│   │   ├── security.py         # JWT handling
│   │   └── logging.py          # Structured logging
│   │
│   ├── domain/                 # Business Logic (Pure)
│   │   ├── models/             # Entities & Value Objects
│   │   ├── services/           # Domain services
│   │   └── repositories/       # Repository interfaces
│   │
│   ├── infrastructure/         # External Dependencies
│   │   ├── database/           # PostgreSQL connection
│   │   ├── neo4j/              # Neo4j driver & queries
│   │   ├── cache/              # Redis caching
│   │   └── storage/            # File storage (S3/Local)
│   │
│   └── agents/                 # AI/ML Components
│       ├── parsers/            # Metadata extraction
│       ├── risk/               # Risk scoring engine
│       └── explanation/        # LLM explanation generator
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── scripts/
└── requirements.txt
```

### 3.2 Frontend Components

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                 # shadcn/ui primitives
│   │   ├── graph/              # React Flow components
│   │   ├── forms/              # Upload, comparison forms
│   │   └── dashboard/          # Dashboard widgets
│   │
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Upload.tsx
│   │   ├── Comparison.tsx
│   │   ├── ImpactAnalysis.tsx
│   │   ├── DependencyGraph.tsx
│   │   ├── ReviewTasks.tsx
│   │   ├── AuditTrail.tsx
│   │   └── History.tsx
│   │
│   ├── hooks/                  # Custom React hooks
│   ├── services/               # API client (TanStack Query)
│   ├── store/                  # State management
│   ├── types/                  # TypeScript types
│   └── utils/                  # Helpers
│
├── package.json
└── vite.config.ts
```

---

## 4. Data Architecture

### 4.1 PostgreSQL Schema (Relational Data)

```sql
-- Users & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Protocols & Versions
CREATE TABLE protocols (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_number VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    therapeutic_area VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE protocol_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id UUID REFERENCES protocols(id),
    version_number VARCHAR(20) NOT NULL,
    effective_date DATE NOT NULL,
    document_path VARCHAR(500),
    sap_section JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(protocol_id, version_number)
);

-- Amendments
CREATE TABLE amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_version_id UUID REFERENCES protocol_versions(id),
    old_text TEXT NOT NULL,
    new_text TEXT NOT NULL,
    change_type VARCHAR(100),
    change_description TEXT,
    semantic_diff JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Impact Analysis Results
CREATE TABLE impact_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID REFERENCES amendments(id),
    risk_summary JSONB,
    total_impacted_nodes INTEGER,
    critical_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Review Tasks
CREATE TABLE review_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    impact_analysis_id UUID REFERENCES impact_analyses(id),
    task_name VARCHAR(255) NOT NULL,
    owner_role VARCHAR(100),
    priority VARCHAR(20),
    estimated_hours DECIMAL(4,2),
    status VARCHAR(50) DEFAULT 'open',
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit Trail
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_protocols_status ON protocols(status);
CREATE INDEX idx_protocol_versions_protocol ON protocol_versions(protocol_id);
CREATE INDEX idx_amendments_status ON amendments(status);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

### 4.2 Neo4j Graph Schema (Dependency Graph)

```cypher
// Node Labels
// :Endpoint
// :Visit
// :Population
// :Dataset {type: 'SDTM' | 'ADaM'}
// :Variable
// :Table
// :Figure
// :ValidationRule
// :DefineXML
// :ReviewTask
// :TLF
// :CSR

// Relationship Types
// (:Endpoint)-[:MEASURED_AT]->(:Visit)
// (:Dataset)-[:CONTAINS_VARIABLE]->(:Variable)
// (:Dataset)-[:DERIVED_FROM]->(:Dataset)
// (:Table)-[:USES_DATASET]->(:Dataset)
// (:Table)-[:DISPLAYS_ENDPOINT]->(:Endpoint)
// (:ValidationRule)-[:VALIDATES]->(:Dataset)
// (:ValidationRule)-[:CHECKS_VARIABLE]->(:Variable)
// (:DefineXML)-[:DESCRIBES]->(:Dataset)
// (:ReviewTask)-[:REQUIRES]->(:Dataset)
// (:TLF)-[:BASED_ON]->(:Table)
// (:CSR)-[:CONTAINS_TLF]->(:TLF)

// Example Graph Construction
MERGE (ep:Endpoint {id: 'primary_endpoint_hba1c', name: 'HbA1c Change from Baseline'})
MERGE (v12:Visit {id: 'week_12', name: 'Week 12', day: 84})
MERGE (v24:Visit {id: 'week_24', name: 'Week 24', day: 168})
MERGE (adlb:Dataset {id: 'adlb', name: 'ADLB', type: 'ADaM'})
MERGE (var_hba1c:Variable {id: 'hba1c', name: 'HbA1c'})
MERGE (tbl14:Table {id: 'table_14_2', name: 'Table 14.2'})
MERGE (rule104:ValidationRule {id: 'rule_104', name: 'Rule 104'})
MERGE (def:DefineXML {id: 'define_v2', version: '2.0'})

MERGE (ep)-[:MEASURED_AT]->(v12)
MERGE (adlb)-[:CONTAINS_VARIABLE]->(var_hba1c)
MERGE (adlb)-[:MEASURES_AT_VISIT]->(v12)
MERGE (tbl14)-[:USES_DATASET]->(adlb)
MERGE (tbl14)-[:DISPLAYS_ENDPOINT]->(ep)
MERGE (rule104)-[:VALIDATES]->(adlb)
MERGE (def)-[:DESCRIBES]->(adlb)
```

### 4.3 Redis Cache Structure

```
# Session Storage
session:{user_id} -> JWT token metadata

# Analysis Results Cache (TTL: 24h)
analysis:{amendment_id}:result -> JSON impact analysis result

# Task Queue
celery:* -> Celery internal queues

# Rate Limiting
ratelimit:{endpoint}:{user_id} -> Counter
```

---

## 5. API Contract

### 5.1 Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 5.2 Core Endpoints

#### POST /api/v1/amendments/upload

Upload protocol/SAP sections for comparison.

```http
POST /api/v1/amendments/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

FormData:
  old_text: string (or file)
  new_text: string (or file)
  protocol_id: UUID (optional)
  change_type: "endpoint" | "visit" | "population" | "variable"

Response:
{
  "amendment_id": "uuid",
  "status": "processing",
  "message": "Amendment uploaded successfully"
}
```

#### POST /api/v1/amendments/compare

Trigger semantic difference detection.

```http
POST /api/v1/amendments/{amendment_id}/compare
Authorization: Bearer {token}

Response:
{
  "amendment_id": "uuid",
  "semantic_diff": {
    "endpoints_changed": ["HbA1c"],
    "visits_changed": {"old": "Week 12", "new": "Week 24"},
    "change_type": "Timing Change",
    "confidence": 0.98
  },
  "status": "completed"
}
```

#### GET /api/v1/impact/{amendment_id}

Get impact analysis results.

```http
GET /api/v1/impact/{amendment_id}
Authorization: Bearer {token}

Response:
{
  "amendment_id": "uuid",
  "total_impacted_nodes": 12,
  "risk_summary": {
    "critical": 2,
    "high": 4,
    "medium": 4,
    "low": 2
  },
  "impacted_nodes": [
    {
      "node_id": "adlb",
      "node_type": "Dataset",
      "name": "ADLB",
      "risk_score": 92,
      "priority": "Critical",
      "reason": "Visit timing changed from Week 12 to Week 24",
      "confidence": 0.98,
      "estimated_rework_hours": 4.0,
      "explanation": "This dataset depends on Week 12 measurements..."
    }
  ]
}
```

#### GET /api/v1/graph/{amendment_id}

Get dependency graph for visualization.

```http
GET /api/v1/graph/{amendment_id}
Authorization: Bearer {token}

Response:
{
  "nodes": [
    {
      "id": "primary_endpoint_hba1c",
      "label": "HbA1c Endpoint",
      "type": "Endpoint",
      "risk_level": "critical",
      "position": {"x": 0, "y": 0}
    }
  ],
  "edges": [
    {
      "source": "primary_endpoint_hba1c",
      "target": "week_12",
      "relationship": "MEASURED_AT",
      "directed": true
    }
  ]
}
```

#### POST /api/v1/review-plan/{amendment_id}

Generate review tasks.

```http
POST /api/v1/review-plan/{amendment_id}
Authorization: Bearer {token}

Response:
{
  "tasks": [
    {
      "task_id": "uuid",
      "task_name": "Rebuild ADLB Dataset",
      "owner_role": "Statistical Programmer",
      "priority": "Critical",
      "estimated_hours": 4.0,
      "dependencies": ["Complete SDTM regeneration"]
    }
  ]
}
```

#### GET /api/v1/audit/{amendment_id}

Get audit trail.

```http
GET /api/v1/audit/{amendment_id}
Authorization: Bearer {token}

Response:
{
  "audit_entries": [
    {
      "timestamp": "2025-01-15T10:30:00Z",
      "user": "john.doe@company.com",
      "action": "AMENDMENT_CREATED",
      "entity_type": "Amendment",
      "entity_id": "uuid",
      "details": {...}
    }
  ]
}
```

#### GET /api/v1/history

Get amendment history for a protocol.

```http
GET /api/v1/history?protocol_id={uuid}&limit=50
Authorization: Bearer {token}

Response:
{
  "amendments": [...]
}
```

---

## 6. Domain Models (Pydantic)

### 6.1 Core Entities

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID

class ChangeType(str, Enum):
    ENDPOINT = "endpoint"
    VISIT = "visit"
    POPULATION = "population"
    VARIABLE = "variable"
    TIMING = "timing"
    METHOD = "method"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NodeType(str, Enum):
    ENDPOINT = "Endpoint"
    VISIT = "Visit"
    POPULATION = "Population"
    DATASET = "Dataset"
    VARIABLE = "Variable"
    TABLE = "Table"
    FIGURE = "Figure"
    VALIDATION_RULE = "ValidationRule"
    DEFINE_XML = "DefineXML"
    REVIEW_TASK = "ReviewTask"
    TLF = "TLF"
    CSR = "CSR"

class SemanticDiff(BaseModel):
    endpoints_changed: List[str] = Field(default_factory=list)
    visits_changed: Optional[Dict[str, str]] = None
    populations_changed: List[str] = Field(default_factory=list)
    variables_changed: List[str] = Field(default_factory=list)
    methods_changed: List[str] = Field(default_factory=list)
    change_type: ChangeType
    change_description: str
    confidence: float = Field(ge=0.0, le=1.0)

class ImpactedNode(BaseModel):
    node_id: str
    node_type: NodeType
    name: str
    risk_score: int = Field(ge=0, le=100)
    priority: RiskLevel
    reason: str
    confidence: float
    estimated_rework_hours: float
    explanation: Optional[str] = None
    downstream_dependencies: List[str] = Field(default_factory=list)

class ImpactAnalysisResult(BaseModel):
    amendment_id: UUID
    semantic_diff: SemanticDiff
    total_impacted_nodes: int
    risk_summary: Dict[RiskLevel, int]
    impacted_nodes: List[ImpactedNode]
    recommendations: List[str]
    generated_at: datetime

class ReviewTask(BaseModel):
    task_id: Optional[UUID] = None
    task_name: str
    owner_role: str
    priority: RiskLevel
    estimated_hours: float
    dependencies: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None

class GraphNode(BaseModel):
    id: str
    label: str
    type: NodeType
    risk_level: Optional[RiskLevel] = None
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    directed: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DependencyGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
```

---

## 7. Agent Orchestration

### 7.1 Processing Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Upload        │────▶│  Semantic Diff   │────▶│  Metadata       │
│   Amendment     │     │  Detection       │     │  Parser         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Audit Log     │◀────│   Review Plan    │◀────│   Risk Engine   │
│   Generation    │     │   Generator      │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        ▲
                                                        │
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Validation    │◀────│   LLM Explanation│◀────│   Impact        │
│   Recommend.    │     │   Layer          │     │   Traversal     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 7.2 Agent Responsibilities

| Agent | Responsibility | LLM Usage |
|-------|---------------|-----------|
| `SemanticDiffAgent` | Extract structured diff from text | Yes - NLP extraction |
| `MetadataParserAgent` | Convert text to structured metadata | Yes - Entity recognition |
| `ImpactTraversalAgent` | Graph traversal (deterministic) | No |
| `RiskEngineAgent` | Calculate risk scores | No - Rule-based |
| `ExplanationAgent` | Generate human-readable explanations | Yes - Translation only |
| `ReviewPlanAgent` | Generate review tasks | Partial - Template filling |

---

## 8. Security & Compliance

### 8.1 Authentication Flow

1. User authenticates via `/auth/login`
2. JWT access token issued (1 hour expiry)
3. Refresh token stored in HttpOnly cookie (7 days)
4. All API requests require `Authorization: Bearer {token}`
5. Role-based access control (RBAC):
   - `admin`: Full access
   - `reviewer`: Read + create tasks
   - `programmer`: Read + update tasks
   - `viewer`: Read-only

### 8.2 Audit Requirements

Every action logged with:
- Timestamp (UTC)
- User ID
- Action type
- Entity affected
- Before/after values
- IP address
- User agent

### 8.3 Data Retention

- Audit logs: 7 years (FDA requirement)
- Protocol versions: Indefinite
- Analysis results: 2 years
- Cache: 24 hours

---

## 9. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Docker Swarm / Kubernetes            │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Frontend  │  │    API      │  │   Workers   │          │
│  │   (Nginx)   │  │  (FastAPI)  │  │   (Celery)  │          │
│  │   :3000     │  │   :8000     │  │   Async     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  PostgreSQL │  │    Neo4j    │  │    Redis    │          │
│  │   :5432     │  │   :7687     │  │   :6379     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Testing Strategy

### 10.1 Unit Tests
- Domain model validation
- Service logic
- Repository methods (mocked DB)
- Pydantic schema validation

### 10.2 Integration Tests
- API endpoint testing
- Neo4j graph queries
- PostgreSQL transactions
- Celery task execution

### 10.3 E2E Tests
- Full amendment workflow
- Graph visualization rendering
- Task generation and assignment

### 10.4 Test Coverage Target
- Minimum 80% line coverage
- 100% coverage on domain layer

---

## 11. Scalability Considerations

### 11.1 Horizontal Scaling
- Stateless API servers behind load balancer
- Celery workers auto-scale based on queue depth
- Neo4j causal clustering for read scaling

### 11.2 Performance Optimization
- Graph queries use indexes on node IDs
- Redis caching for frequently accessed analyses
- Pagination on all list endpoints
- Async I/O throughout

### 11.3 Future Enhancements
- Multi-protocol comparison
- Batch amendment processing
- Real-time collaboration
- ML-based risk prediction
- Integration with Pinnacle21 API
- SAP automated parsing

---

## 12. Technology Stack Summary

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend | React + TypeScript | Type safety, enterprise adoption |
| UI Components | shadcn/ui + Tailwind | Rapid development, consistent design |
| Graph Viz | React Flow | Interactive, performant |
| State | TanStack Query | Server state management |
| Backend | FastAPI | Async, auto OpenAPI docs |
| Validation | Pydantic | Shared schemas |
| Graph DB | Neo4j | Native graph traversal |
| Relational DB | PostgreSQL | ACID compliance |
| Cache | Redis | Low-latency caching |
| Task Queue | Celery + Redis | Async processing |
| Auth | JWT + bcrypt | Industry standard |
| Container | Docker | Reproducible builds |

---

## 13. Folder Structure (Final)

```
/workspace/
├── ARCHITECTURE.md              # This document
├── README.md                    # Project overview
├── docker-compose.yml           # Local development
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── amendments.py
│   │   │   │   ├── impact.py
│   │   │   │   ├── graph.py
│   │   │   │   ├── review.py
│   │   │   │   └── audit.py
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       └── logging.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── entities.py
│   │   │   │   └── value_objects.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── amendment_service.py
│   │   │   │   ├── impact_service.py
│   │   │   │   └── review_service.py
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── interfaces.py
│   │   │       ├── postgres_repo.py
│   │   │       └── neo4j_repo.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── __init__.py
│   │   │   │   └── postgres.py
│   │   │   ├── neo4j/
│   │   │   │   ├── __init__.py
│   │   │   │   └── driver.py
│   │   │   ├── cache/
│   │   │   │   ├── __init__.py
│   │   │   │   └── redis.py
│   │   │   └── storage/
│   │   │       └── local.py
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── parsers/
│   │       │   ├── __init__.py
│   │       │   └── semantic_parser.py
│   │       ├── risk/
│   │       │   ├── __init__.py
│   │       │   └── risk_engine.py
│   │       └── explanation/
│   │           ├── __init__.py
│   │           └── llm_explainer.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   └── integration/
│   ├── scripts/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docs/
│   ├── api.md
│   └── deployment.md
├── examples/
│   ├── sample_amendment.json
│   └── sample_graph.json
└── tests/
    ├── unit/
    └── integration/
```

---

## 14. Implementation Phases

### Phase 1: Foundation (Current)
- Project scaffolding
- Database schemas
- Basic API endpoints
- Neo4j graph setup
- Simple metadata parser

### Phase 2: Core Features
- Semantic diff detection
- Impact traversal
- Risk engine
- Review task generation

### Phase 3: AI Integration
- LLM metadata extraction
- Explanation generation
- Confidence scoring

### Phase 4: Frontend
- Dashboard UI
- Graph visualization
- Task management

### Phase 5: Polish
- Testing
- Documentation
- Performance optimization
- Security hardening

---

*Document Version: 1.0*
*Last Updated: 2025-01-15*
*Author: Principal Software Architect*
