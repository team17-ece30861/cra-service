from ninja import NinjaAPI, Schema
from ninja.errors import ValidationError

from core import controls
from cra_service.errors import install_exception_handlers
from cra_service.validation import JSONParser, field_errors


class ServiceAPI(NinjaAPI):
    """NinjaAPI with problem+json errors (cra_service.errors) and openapi.yaml's
    validation rules: schema errors are 400, never ninja's default 422."""

    def __init__(self, **kwargs):
        kwargs.setdefault("parser", JSONParser())
        super().__init__(**kwargs)

    def set_default_exception_handlers(self) -> None:
        install_exception_handlers(self)

    def validation_error_from_error_contexts(self, error_contexts) -> ValidationError:
        errors = []
        for context in error_contexts:
            model = context.model
            source = model.__ninja_param_source__  # "body", "header", "query", "path"
            # A single body parameter is nested under its name; drop it.
            skip = 1 if getattr(model, "__read_from_single_attr__", None) else 0
            raw = [
                {**e, "loc": model.__ninja_flatten_map_reverse__.get(e["loc"], e["loc"])}
                for e in context.pydantic_validation_error.errors(include_url=False)
            ]
            for entry in field_errors(raw, skip=skip, root=source):
                errors.append({"source": source, **entry})
        return ValidationError(errors)


api = ServiceAPI(
    title="Team 17 CRA Reporting Service",
    version="0.1.0",
    docs_url="/docs",  # convenience only; the pod's shared openapi.yaml is the contract
)


class HealthOut(Schema):
    status: str


@api.get("/health", response=HealthOut)
def health(request):
    """Liveness check. Deliberately does not touch the database, so it stays
    fast and doesn't wake Neon. Align the response with the shared OpenAPI file."""
    return {"status": "ok"}


api.add_router("/test", controls.router)
