"""
Secured API Documentation Endpoints.

Provides authenticated access to API documentation in production.

In development:
- /docs, /redoc, /openapi.json are publicly accessible

In production:
- Standard docs URLs are disabled
- /api/v1/docs/swagger requires authentication
- /api/v1/docs/redoc requires authentication
- /api/v1/docs/openapi.json requires authentication

Security:
- Uses the same JWT token validation as other API endpoints
- Rate limited to prevent abuse
- Logs access for audit trail
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from core.config import settings
from core.logging import get_logger
from api.deps import get_current_user

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# SWAGGER UI (Authenticated)
# =============================================================================

@router.get(
    "/swagger",
    response_class=HTMLResponse,
    summary="Swagger UI (Authenticated)",
    description="Interactive API documentation. Requires authentication in production.",
    include_in_schema=False,
)
async def get_swagger_documentation(
    request: Request,
    current_user = Depends(get_current_user),
):
    """
    Serve Swagger UI for authenticated users.
    
    This endpoint provides the same interactive documentation as /docs,
    but requires a valid JWT token in production.
    """
    logger.info(
        f"API docs accessed",
        extra={
            "user_id": getattr(current_user, 'uuid', 'unknown'),
            "endpoint": "swagger",
        }
    )
    
    return get_swagger_ui_html(
        openapi_url=f"{settings.api_v1_prefix}/docs/openapi.json",
        title=f"{settings.app_name} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# =============================================================================
# REDOC (Authenticated)
# =============================================================================

@router.get(
    "/redoc",
    response_class=HTMLResponse,
    summary="ReDoc (Authenticated)",
    description="Alternative API documentation. Requires authentication in production.",
    include_in_schema=False,
)
async def get_redoc_documentation(
    request: Request,
    current_user = Depends(get_current_user),
):
    """
    Serve ReDoc for authenticated users.
    
    This endpoint provides the same documentation as /redoc,
    but requires a valid JWT token in production.
    """
    logger.info(
        f"API docs accessed",
        extra={
            "user_id": getattr(current_user, 'uuid', 'unknown'),
            "endpoint": "redoc",
        }
    )
    
    return get_redoc_html(
        openapi_url=f"{settings.api_v1_prefix}/docs/openapi.json",
        title=f"{settings.app_name} - API Documentation",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# =============================================================================
# OPENAPI SCHEMA (Authenticated)
# =============================================================================

@router.get(
    "/openapi.json",
    response_class=JSONResponse,
    summary="OpenAPI Schema (Authenticated)",
    description="OpenAPI 3.0 schema. Requires authentication in production.",
    include_in_schema=False,
)
async def get_openapi_schema(
    request: Request,
    current_user = Depends(get_current_user),
):
    """
    Serve OpenAPI schema for authenticated users.
    
    Returns the complete OpenAPI 3.0 specification for the API.
    Useful for generating client libraries or importing into tools.
    """
    logger.info(
        f"OpenAPI schema accessed",
        extra={
            "user_id": getattr(current_user, 'uuid', 'unknown'),
        }
    )
    
    # Get the OpenAPI schema from the main app
    from main import app
    return JSONResponse(content=app.openapi())


# =============================================================================
# DOCS INDEX (Shows available documentation)
# =============================================================================

@router.get(
    "",
    response_class=HTMLResponse,
    summary="API Documentation Index",
    description="List of available API documentation endpoints.",
)
async def docs_index(
    request: Request,
    current_user = Depends(get_current_user),
):
    """
    Documentation landing page with links to Swagger and ReDoc.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{settings.app_name} - API Documentation</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #333;
                margin-bottom: 10px;
            }}
            .subtitle {{
                color: #666;
                margin-bottom: 30px;
            }}
            .user-info {{
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 30px;
            }}
            .doc-links {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
            }}
            .doc-card {{
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                text-decoration: none;
                color: #333;
                transition: all 0.3s ease;
            }}
            .doc-card:hover {{
                border-color: #667eea;
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.2);
                transform: translateY(-2px);
            }}
            .doc-card h3 {{
                margin: 0 0 10px 0;
                color: #667eea;
            }}
            .doc-card p {{
                margin: 0;
                color: #666;
                font-size: 14px;
            }}
            .badge {{
                display: inline-block;
                background: #e8f5e9;
                color: #2e7d32;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 {settings.app_name}</h1>
            <p class="subtitle">API Documentation</p>
            
            <div class="user-info">
                <strong>✓ Authenticated as:</strong> {getattr(current_user, 'email', 'Unknown')}
            </div>
            
            <div class="doc-links">
                <a href="{settings.api_v1_prefix}/docs/swagger" class="doc-card">
                    <h3>🔧 Swagger UI</h3>
                    <p>Interactive API explorer with the ability to test endpoints directly.</p>
                    <span class="badge">Recommended</span>
                </a>
                
                <a href="{settings.api_v1_prefix}/docs/redoc" class="doc-card">
                    <h3>📖 ReDoc</h3>
                    <p>Clean, readable API documentation with better navigation.</p>
                </a>
                
                <a href="{settings.api_v1_prefix}/docs/openapi.json" class="doc-card">
                    <h3>📋 OpenAPI Schema</h3>
                    <p>Raw OpenAPI 3.0 specification for client generation.</p>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
