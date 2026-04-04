"""Export Pydantic JSON schemas for frontend drift detection."""
import json
from pathlib import Path
from src.api.schemas.admin_graphics import PublicationResponse

output_dir = Path(__file__).parent.parent / "schemas"
output_dir.mkdir(exist_ok=True)

schema = PublicationResponse.model_json_schema()
output_path = output_dir / "publication_response.schema.json"
output_path.write_text(json.dumps(schema, indent=2))
print(f"Exported: {output_path}")
