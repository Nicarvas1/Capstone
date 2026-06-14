"""Entry point: python run_voice.py"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "voice_assistant.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
