from fastapi import FastAPI, HTTPException, Request
import random
import logging
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.responses import Response
import time
from logging_loki import LokiHandler
from logging import StreamHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_app")

# Add Loki handler
loki_handler = LokiHandler(
    url="http://loki:3100/loki/api/v1/push",
    tags={"application": "fastapi_app"},
    version="1",
)
logger.addHandler(loki_handler)

# Also keep console logging
console_handler = StreamHandler()
logger.addHandler(console_handler)

# Create a FastAPI app
app = FastAPI()

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Custom Prometheus metrics
REQUESTS = Counter('fastapi_custom_requests_total', 'Total FastAPI Requests')
RANDOM_NUMBERS = Counter('fastapi_random_numbers_total', 'Total random numbers generated')
WARNINGS = Counter('fastapi_warnings_total', 'Total warnings triggered')
ERRORS = Counter('fastapi_errors_total', 'Total errors triggered')

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Request processed in {process_time:.2f} seconds", extra={"tags": {"endpoint": request.url.path}})
    REQUESTS.inc()
    return response

@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed", extra={"tags": {"endpoint": "/"}})
    return {"Hello": "World"}

@app.get("/random_log")
async def random_log():
    random_number = random.randint(1, 100)
    logger.info(f"Generated random number: {random_number}", extra={"tags": {"endpoint": "/random_log", "random_number": random_number}})
    RANDOM_NUMBERS.inc()
    return {'random_number': random_number}

@app.get("/trigger_warning")
async def trigger_warning():
    logger.warning("This is a warning log.", extra={"tags": {"endpoint": "/trigger_warning"}})
    WARNINGS.inc()
    return {"message": "Warning triggered"}

@app.get("/trigger_error")
async def trigger_error():
    logger.error("This is an error log.", extra={"tags": {"endpoint": "/trigger_error"}})
    ERRORS.inc()
    raise HTTPException(status_code=500, detail="Error triggered")

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)