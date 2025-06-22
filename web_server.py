from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "✅ Temp Mail Bot is running."}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=10000)
