import argparse
import os
import time
from http import HTTPStatus
from typing import Dict

import ray
import uvicorn
from fastapi import FastAPI, Request

from madewithml import evaluate, predict
from madewithml.config import MLFLOW_TRACKING_URI, mlflow

# 1. Define application
app = FastAPI(
    title="Made With ML",
    description="Classify machine learning projects.",
    version="0.1",
)

# Global variables to hold the model and settings
predictor = None
run_id = None
threshold = 0.9

@app.on_event("startup")
async def startup_event():
    """Load model and initialize tracking on startup."""
    global predictor, run_id
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    best_checkpoint = predict.get_best_checkpoint(run_id=run_id)
    predictor = predict.TorchPredictor.from_checkpoint(best_checkpoint)
    print(f"--- Model loaded successfully from run: {run_id} ---")

@app.get("/")
def _index() -> Dict:
    """Health check."""
    return {
        "message": HTTPStatus.OK.phrase,
        "status-code": HTTPStatus.OK,
        "data": {},
    }

@app.get("/run_id/")
def _run_id() -> Dict:
    """Get the run ID."""
    return {"run_id": run_id}

@app.post("/evaluate/")
async def _evaluate(request: Request) -> Dict:
    """Evaluate the model on a dataset."""
    data = await request.json()
    results = evaluate.evaluate(run_id=run_id, dataset_loc=data.get("dataset"))
    return {"results": results}

@app.post("/predict/")
async def _predict(request: Request):
    """Predict tags with a threshold for 'other' class."""
    data = await request.json()
    # Use Ray Data as in the original implementation
    sample_ds = ray.data.from_items([
        {"title": data.get("title", ""), "description": data.get("description", ""), "tag": ""}
    ])
    
    results = predict.predict_proba(ds=sample_ds, predictor=predictor)

    # Apply custom threshold logic
    for i, result in enumerate(results):
        pred = result["prediction"]
        prob = result["probabilities"]
        if prob[pred] < threshold:
            results[i]["prediction"] = "other"

    return {"results": results}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", help="run ID to use for serving.")
    parser.add_argument("--threshold", type=float, default=0.9, help="threshold for `other` class.")
    args = parser.parse_args()
    
    # Assign to globals so the FastAPI app can access them
    run_id = args.run_id
    threshold = args.threshold
    
    # Initialize Ray for data processing logic
    ray.init(runtime_env={"env_vars": {"GITHUB_USERNAME": os.environ.get("GITHUB_USERNAME", "")}})
    
    # Start the server using Uvicorn
    print(f"--- Starting Uvicorn server on http://0.0.0.0:8000 ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)