import uvicorn
from pathlib import Path

if __name__ == "__main__":
    app_dir = Path(__file__).resolve().parent / "app"
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=[str(app_dir)])
