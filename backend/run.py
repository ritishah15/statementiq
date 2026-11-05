import os
import uvicorn
from pathlib import Path

if __name__ == "__main__":
    app_dir = Path(__file__).resolve().parent / "app"
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    reload = os.environ.get("ENV") != "production"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload, reload_dirs=[str(app_dir)] if reload else None)
