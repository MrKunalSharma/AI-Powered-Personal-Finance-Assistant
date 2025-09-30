from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

@app.post("/test-register")
def test_register(user: UserCreate):
    return {
        "message": "Received registration request",
        "email": user.email,
        "username": user.username
    }

if __name__ == "__main__":
    print("Starting minimal test server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
