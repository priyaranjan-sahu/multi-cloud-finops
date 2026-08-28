"""Application entry point for the FinOps API server."""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("finops_engine.api.app:app", host="0.0.0.0", port=8000, reload=True)
