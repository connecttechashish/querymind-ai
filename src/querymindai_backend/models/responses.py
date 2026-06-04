from pydantic import BaseModel

class RootResponse(BaseModel):
    message: str
    app_name: str
    version: str

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
