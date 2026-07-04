"""
FastAPI application factory.

Creates and configures the main FastAPI application with all middleware,
routes, and lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.infrastructure.database.postgres import init_db
from app.infrastructure.neo4j.driver import init_neo4j, close_neo4j
from app.infrastructure.cache.redis import init_redis, close_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("Starting up Protocol Amendment Dependency Graph Engine...")
    init_db()
    init_neo4j()
    init_redis()

    # Initialize Neo4j graph with default structure
    from app.infrastructure.neo4j.driver import Neo4jRepository

    graph_repo = Neo4jRepository()
    await graph_repo.initialize_graph()

    yield

    # Shutdown
    print("Shutting down...")
    await close_neo4j()
    await close_redis()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## Protocol Amendment Dependency Graph Engine

A production-grade system for analyzing clinical protocol amendments and identifying downstream impact across clinical trial assets.

### Features

- **Semantic Difference Detection**: Automatically identify changes in protocol text
- **Dependency Graph**: Graph-based model of clinical trial asset relationships
- **Impact Analysis**: Traverse dependencies to find all affected assets
- **Risk Scoring**: Calculate risk levels (0-100) for each impacted node
- **Review Tasks**: Generate actionable tasks for remediation
- **Audit Trail**: Complete traceability for FDA compliance
- **Interactive Visualization**: React Flow-based dependency graph viewer

### Key Endpoints

- `POST /api/v1/amendments/upload` - Upload protocol amendment
- `POST /api/v1/amendments/{id}/compare` - Analyze semantic differences
- `GET /api/v1/impact/{id}` - Get impact analysis results
- `GET /api/v1/graph/{id}` - Get dependency graph for visualization
- `POST /api/v1/review-plan/{id}` - Generate review tasks
- `GET /api/v1/audit/{id}` - Get audit trail
        """,
        openapi_tags=[
            {
                "name": "Authentication",
                "description": "User authentication and authorization",
            },
            {
                "name": "Amendments",
                "description": "Protocol amendment management",
            },
            {
                "name": "Impact Analysis",
                "description": "Impact analysis and risk assessment",
            },
            {
                "name": "Graph",
                "description": "Dependency graph operations",
            },
            {
                "name": "Review",
                "description": "Review task management",
            },
            {
                "name": "Audit",
                "description": "Audit trail and compliance",
            },
        ],
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from app.api.routes import auth, amendments, impact, graph, review, audit

    app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])
    app.include_router(amendments.router, prefix=f"{settings.api_prefix}/amendments", tags=["Amendments"])
    app.include_router(impact.router, prefix=f"{settings.api_prefix}/impact", tags=["Impact Analysis"])
    app.include_router(graph.router, prefix=f"{settings.api_prefix}/graph", tags=["Graph"])
    app.include_router(review.router, prefix=f"{settings.api_prefix}/review", tags=["Review"])
    app.include_router(audit.router, prefix=f"{settings.api_prefix}/audit", tags=["Audit"])

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.app_version,
        }

    return app


# Create application instance
app = create_app()
