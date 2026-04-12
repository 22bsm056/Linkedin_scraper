from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from routers.profile import router as profile_router

app = FastAPI(
    title="LinkedIn Scraper API",
    description="Stealth LinkedIn Scraper Microservice",
    version="1.0.0"
)

# Exception handlers to match standard schema
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "success" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
        
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "rateLimitRemaining": 0,
            "rateLimitReset": 0,
            "data": None,
            "error": "HTTP Error",
            "message": str(exc.detail)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "rateLimitRemaining": 0,
            "rateLimitReset": 0,
            "data": None,
            "error": "Unprocessable Entity",
            "message": str(exc.errors())
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "rateLimitRemaining": 0,
            "rateLimitReset": 0,
            "data": None,
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )

app.include_router(profile_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
