import argparse
import os
import time
from http import HTTPStatus
from typing import Dict

import ray
from fastapi import FastAPI, Response
from ray import serve
from starlette.requests import Request

import json
from numpyencoder import NumpyEncoder

from madewithml import evaluate, predict
from madewithml.config import MLFLOW_TRACKING_URI, mlflow

# ── Separate app for metrics only ────────────────────────────────────────────
# Keep this app free of any prometheus imports at module level so cloudpickle
# never tries to serialize thread locks embedded in the REGISTRY object.
metrics_app = FastAPI(title="Metrics")

@metrics_app.get("/metrics")
def metrics():
    # Lazy import so the registry is only touched at request time, not at
    # class-definition / pickling time.
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, REGISTRY
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

# ── Main inference app ────────────────────────────────────────────────────────
app = FastAPI(
    title="Made With ML",
    description="Classify machine learning projects.",
    version="0.1",
)

@serve.deployment(num_replicas=1, ray_actor_options={"num_cpus": 0, "num_gpus": 0})
@serve.ingress(app)
class ModelDeployment:
    def __init__(self, run_id: str, threshold: float = 0.9):
        self.run_id = run_id
        self.threshold = threshold
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        best_checkpoint = predict.get_best_checkpoint(run_id=run_id)
        self.predictor = predict.TorchPredictor.from_checkpoint(best_checkpoint)

    @app.get("/")
    def _index(self) -> Dict:
        """Health check."""
        return {
            "message": HTTPStatus.OK.phrase,
            "status-code": HTTPStatus.OK,
            "data": {},
        }

    @app.get("/run_id/")
    def _run_id(self) -> Dict:
        return {"run_id": self.run_id}

    @app.post("/evaluate/")
    async def _evaluate(self, request: Request) -> Dict:
        data = await request.json()
        results = evaluate.evaluate(run_id=self.run_id, dataset_loc=data.get("dataset"))
        return {"results": results}

    @app.post("/predict/")
    async def _predict(self, request: Request):
        data = await request.json()
        sample_ds = ray.data.from_items([{
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "tag": "other",
        }])
        results = predict.predict_proba(ds=sample_ds, predictor=self.predictor)

        for i, result in enumerate(results):
            pred = result["prediction"]
            prob = result["probabilities"]
            if prob[pred] < self.threshold:
                results[i]["prediction"] = "other"

        safe_results = json.loads(json.dumps(results, cls=NumpyEncoder))
        return {"results": safe_results}


# ── Metrics deployment (lightweight, no ML deps) ──────────────────────────────
@serve.deployment(num_replicas=1, ray_actor_options={"num_cpus": 0, "num_gpus": 0})
@serve.ingress(metrics_app)
class MetricsDeployment:
    pass  # all logic lives in the route above


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", help="run ID to use for serving.")
    parser.add_argument("--threshold", type=float, default=0.9, help="threshold for `other` class.")
    args = parser.parse_args()

    ray.init(runtime_env={"env_vars": {"GITHUB_USERNAME": os.environ.get("GITHUB_USERNAME", "")}})

    serve.run(
        # Route /metrics to MetricsDeployment, everything else to ModelDeployment
        serve.application(
            ModelDeployment.bind(run_id=args.run_id, threshold=args.threshold),
        ),
        host="0.0.0.0",
        port=8000,
    )

    # Run MetricsDeployment on a separate port so Prometheus can scrape it
    # without conflicting with the inference traffic.
    serve.run(
        MetricsDeployment.bind(),
        name="metrics",
        host="0.0.0.0",
        port=8001,
        route_prefix="/",
    )

    while True:
        time.sleep(60)