"""在 ai-vpr-ser 目录下：python run_server.py"""

import uvicorn

from app.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        workers=1,
    )
