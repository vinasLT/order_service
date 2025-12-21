import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Callable

from aio_pika import connect_robust
from fastapi import FastAPI
from fastapi_pagination import add_pagination
from fastapi_problem.handler import new_exception_handler, add_exception_handler

from app.database.db.session import AsyncSessionLocal
from app.routers import api_router
from app.config import settings
from app.core.logger import logger
from app.services.rabbit_service.file_routing_keys import RoutingKeys
from app.services.rabbit_service.order_consumer import OrderRabbitConsumer


def setup_middleware_and_handlers(app: FastAPI):
    eh = new_exception_handler()
    add_exception_handler(app, eh)

def setup_routers(app: FastAPI):
    app.include_router(api_router)
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

def create_app(
        lifespan_override: Optional[Callable] = None
) -> FastAPI:
    @asynccontextmanager
    async def default_lifespan(_: FastAPI):
        max_attempts = 5
        base_delay_s = 2
        connection = None
        for attempt in range(1, max_attempts + 1):
            try:
                connection = await connect_robust(settings.RABBITMQ_URL)
                break
            except Exception:
                if attempt >= max_attempts:
                    raise
                delay = base_delay_s * attempt
                logger.warning(
                    "RabbitMQ connection failed, retrying",
                    extra={"attempt": attempt, "delay_s": delay},
                )
                await asyncio.sleep(delay)

        if connection is None:
            raise RuntimeError("RabbitMQ connection not established after retries")
        consumer = OrderRabbitConsumer(
            AsyncSessionLocal,
            connection,
            [member.value for member in RoutingKeys],

        )
        await consumer.set_up()
        await consumer.start_consuming()

        logger.info(f"{settings.APP_NAME} started!")
        yield
        await consumer.stop_consuming()


    docs_url = "/docs" if settings.enable_docs else None
    redoc_url = "/redoc" if settings.enable_docs else None
    openapi_url = "/openapi.json" if settings.enable_docs else None

    app = FastAPI(
        title="Order service",
        description="Create and manage orders",
        version="0.0.1",
        root_path=settings.ROOT_PATH,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan_override or default_lifespan
    )

    add_pagination(app)

    setup_middleware_and_handlers(app)
    setup_routers(app)

    return app
