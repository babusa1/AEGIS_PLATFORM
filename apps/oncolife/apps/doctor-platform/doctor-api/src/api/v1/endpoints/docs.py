"""
Secured API Documentation Endpoints for Doctor API.

Provides authenticated access to API documentation in production.

In development: /docs, /redoc are publicly accessible
In production: /api/v1/docs/* requires authentication
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from core.config import settings
from core.logging import get_logger
from api.deps import get_current_user

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/swagger",
    response_class=HTMLResponse,
    summary="Swagger UI (Authenticated)",
    include_in_schema=False,
)
async def get_swagger_documentation(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Serve Swagger UI for authenticated users."""
    logger.info(
        f"API docs accessed",
        extra={
            "user_id": getattr(current_user, 'uuid', 'unknown'),
            "endpoint": "swagger",
        }
    )
    
    return get_swagger_ui_html(
        openapi_url="/api/v1/docs/openapi.json",
        title=f"{settings.app_name} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@router.get(
    "/redoc",
    response_class=HTMLResponse,
    summary="ReDoc (Authenticated)",
    include_in_schema=False,
)
async def get_redoc_documentation(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Serve ReDoc for authenticated users."""
    logger.info(
        f"API docs accessed",
        extra={
            "user_id": getattr(current_user, 'uuid', 'unknown'),
            "endpoint": "redoc",
        }
    )
    
    return get_redoc_html(
        openapi_url="/api/v1/docs/openapi.json",
        title=f"{settings.app_name} - API Documentation",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


@router.get(
    "/openapi.json",
    response_class=JSONResponse,
    summary="OpenAPI Schema (Authenticated)",
    include_in_schema=False,
)
async def get_openapi_schema(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Serve OpenAPI schema for authenticated users."""
    from main import app
    return JSONResponse(content=app.openapi())


@router.get(
    "",
    response_class=HTMLResponse,
    summary="API Documentation Index",
)
async def docs_index(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Documentation landing page."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{settings.app_name} - API Documentation</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ color: #1e3a5f; margin-bottom: 10px; }}
            .subtitle {{ color: #666; margin-bottom: 30px; }}
            .user-info {{
                background: #e3f2fd;
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
                border-color: #1e3a5f;
                box-shadow: 0 5px 20px rgba(30, 58, 95, 0.2);
                transform: translateY(-2px);
            }}
            .doc-card h3 {{ margin: 0 0 10px 0; color: #1e3a5f; }}
            .doc-card p {{ margin: 0; color: #666; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 {settings.app_name}</h1>
            <p class="subtitle">API Documentation - Doctor Portal</p>
            
            <div class="user-info">
                <strong>✓ Authenticated as:</strong> {getattr(current_user, 'email', 'Unknown')}
            </div>
            
            <div class="doc-links">
                <a href="/api/v1/docs/swagger" class="doc-card">
                    <h3>🔧 Swagger UI</h3>
                    <p>Interactive API explorer with testing capabilities.</p>
                </a>
                
                <a href="/api/v1/docs/redoc" class="doc-card">
                    <h3>📖 ReDoc</h3>
                    <p>Clean, readable API documentation.</p>
                </a>
                
                <a href="/api/v1/docs/openapi.json" class="doc-card">
                    <h3>📋 OpenAPI Schema</h3>
                    <p>Raw OpenAPI 3.0 specification.</p>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
