import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.backend.api.main:app", host="127.0.0.1", port=8002, reload=True)
