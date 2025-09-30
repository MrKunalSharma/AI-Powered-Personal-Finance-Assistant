# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# import uvicorn
# import os

# from src.database.database import engine
# from src.database import models
# from src.api.routes import router

# # Create database tables
# models.Base.metadata.create_all(bind=engine)

# # Initialize FastAPI app
# app = FastAPI(
#     title="AI Finance Assistant API",
#     description="Backend API for AI-powered personal finance management",
#     version="1.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc"
# )

# # Configure CORS for production
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "https://your-streamlit-app.streamlit.app",  # Your Streamlit URL
#         "http://localhost:8501",  # Local development
#         "*"  # Allow all origins (change in production)
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Include routes
# app.include_router(router, prefix="/api/v1")

# @app.get("/")
# def read_root():
#     return {
#         "message": "AI Finance Assistant API",
#         "documentation": "/docs",
#         "health": "/health",
#         "version": "1.0.0"
#     }

# @app.get("/health")
# def health_check():
#     return {"status": "healthy", "service": "ai-finance-api"}

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run("main:app", host="0.0.0.0", port=port)


from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}
