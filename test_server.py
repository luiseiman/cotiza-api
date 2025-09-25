
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "healthy", "message": "Test server running"}

@app.get("/test")
def test():
    return {"test": "success", "timestamp": "2024-01-01T00:00:00Z"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
