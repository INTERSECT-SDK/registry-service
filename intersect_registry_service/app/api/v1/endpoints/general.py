from fastapi import APIRouter, Request, Response
from sqlmodel import text

router = APIRouter()


@router.get(
    '/ping',
    tags=['Ping'],
    description='Application ping',
    response_description=('empty response, 204 if able to execute and 5xx if not'),
)
async def ping() -> Response:
    """rudimentary ping"""
    return Response(status_code=204)


@router.get(
    '/healthcheck',
    tags=['Healthcheck'],
    description='Application healthcheck',
    response_description=(
        "Array of errors explaining why the service won't work (if empty array: all OK)"
    ),
)
async def healthcheck(req: Request) -> Response:
    """This can be used as a healthcheck endpoint for, e.g. Kubernetes."""
    # check DB connection first
    with req.app.state.db.connect() as connection:
        connection.execute(text('SELECT 1'))

    # check that we're connected to the broker
    return Response()
