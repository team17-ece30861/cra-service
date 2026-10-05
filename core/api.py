from ninja import NinjaAPI, Schema

api = NinjaAPI(
    title="Team 17 CRA Reporting Service",
    version="0.1.0",
    docs_url="/docs",  # convenience only; the pod's shared openapi.yaml is the contract
)


class HealthOut(Schema):
    status: str


@api.get("/health", response=HealthOut, auth=None)
def health(request):
    """Liveness check. Deliberately does not touch the database, so it stays
    fast and doesn't wake Neon. Align the response with the shared OpenAPI file."""
    return {"status": "ok"}
