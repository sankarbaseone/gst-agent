from fastapi import FastAPI
from app.core.config import settings
from app.api import health
# from app.db.session import db # Can be imported when needed for startup hooks

app = FastAPI(title=settings.PROJECT_NAME)

# Include routers
app.include_router(health.router)

from app.api import invoices, explanation
app.include_router(invoices.router)
app.include_router(explanation.router)

@app.on_event("startup")
async def startup_event():
    # Placeholder for database connection
    # await db.connect()
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # Placeholder for database disconnection
    # await db.disconnect()
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
