import os
import uvicorn
from budget_ai.api.app import app

def main():
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("budget_ai.api.app:app", host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
