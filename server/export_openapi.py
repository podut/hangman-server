"""Script to export OpenAPI specification from FastAPI app."""

import json
import sys
from pathlib import Path

# Add server/src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import app


def export_openapi_spec():
    """Export OpenAPI spec to JSON and YAML formats."""
    
    # Get OpenAPI schema from FastAPI
    openapi_schema = app.openapi()
    
    # Add additional documentation
    openapi_schema["info"]["description"] = """
## Hangman Server API

REST API pentru jocul Hangman cu suport pentru:
- Autentificare utilizatori (JWT)
- Sesiuni de joc (1, 100 sau N jocuri)
- Statistici și leaderboard
- Administrare dicționare (admin)
- GDPR compliance (ștergere cont, export date)
- Rate limiting
- Paginare cu Link headers (RFC 5988)

### Autentificare

Majoritatea endpoint-urilor necesită autentificare prin JWT token în header:
```
Authorization: Bearer <token>
```

Token-ul se obține prin POST /api/v1/auth/login.

### Rate Limiting

- General: 100 req/min per token
- Sesiuni: 10 creări/min per utilizator  
- Jocuri: 5 creări/min per sesiune

### Paginare

Endpoint-urile paginate returnează Link headers conform RFC 5988:
```
Link: </api/v1/sessions/{id}/games?page=1>; rel="first", 
      </api/v1/sessions/{id}/games?page=5>; rel="last",
      </api/v1/sessions/{id}/games?page=3>; rel="next"
```

### GDPR Compliance

- DELETE /api/v1/users/me - Ștergere cont (Article 17)
- GET /api/v1/users/me/export - Export date (Article 20)
"""
    
    openapi_schema["info"]["contact"] = {
        "name": "Hangman API Support",
        "email": "support@hangman-api.example.com"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    # Add tags descriptions
    openapi_schema["tags"] = [
        {
            "name": "auth",
            "description": "Autentificare și gestionare utilizatori"
        },
        {
            "name": "sessions",
            "description": "Crearea și gestionarea sesiunilor de joc"
        },
        {
            "name": "games",
            "description": "Jocuri Hangman individuale"
        },
        {
            "name": "stats",
            "description": "Statistici utilizatori și leaderboard"
        },
        {
            "name": "admin",
            "description": "Endpoint-uri administrative (necesită rol admin)"
        },
        {
            "name": "health",
            "description": "Health checks și informații server"
        }
    ]
    
    # Save as JSON
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    json_path = docs_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✓ OpenAPI JSON exported to: {json_path}")
    
    # Save as YAML
    try:
        import yaml
        yaml_path = docs_dir / "openapi.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"✓ OpenAPI YAML exported to: {yaml_path}")
    except ImportError:
        print("⚠ PyYAML not installed. Skipping YAML export. Install with: pip install pyyaml")
        print("   Run: pip install pyyaml")
    
    print(f"\n📊 API Summary:")
    print(f"   Title: {openapi_schema['info']['title']}")
    print(f"   Version: {openapi_schema['info']['version']}")
    print(f"   Endpoints: {len(openapi_schema.get('paths', {}))}")
    print(f"   Schemas: {len(openapi_schema.get('components', {}).get('schemas', {}))}")


if __name__ == "__main__":
    export_openapi_spec()
