pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
        PYTHONPATH = "${WORKSPACE}"
        // Make sure your username is still set here!
        GITHUB_USERNAME = 'your_github_username_here' 
        RAY_SERVE_PROXY_READY_CHECK_TIMEOUT_S = '120'
    }

    stages {
        // ==========================================
        // 0. ENVIRONMENT SETUP
        // ==========================================
        stage('Install Global Dependencies') {
            steps {
                echo 'Installing dependencies directly into the Docker container...'
                sh '''
                    python3 -m pip install --upgrade pip wheel --root-user-action=ignore
                    python3 -m pip install "setuptools<70.0.0" --root-user-action=ignore
                    python3 -m pip install --no-cache-dir -r requirements.txt --root-user-action=ignore
                    
                    # MAGICAL FIX: Upgrade typer and click AFTER requirements.txt 
                    # so the buggy version is permanently overwritten!
                    python3 -m pip install --upgrade typer click --root-user-action=ignore
                '''
            }
        }

        // =========================================
        // 1. WORKLOADS WORKFLOW
        // =========================================
        stage('Model Development Workloads') {
            when {
                anyOf {
                    changeRequest()
                    branch 'main'
                }
            }
            steps {
                echo "Running training..."
                sh '''
                    python3 madewithml/train.py \
                        --experiment-name="llm-classification" \
                        --dataset-loc="$(pwd)/datasets/dataset.csv" \
                        --train-loop-config='{"dropout_p": 0.5, "lr": 1e-4, "lr_factor": 0.8, "lr_patience": 3, "num_epochs": 1, "batch_size": 2}' \
                        --num-samples=20 \
                        --num-workers=1 \
                        --cpu-per-worker=1 \
                        --gpu-per-worker=0
                '''
            }
        }

        // ==========================================
        // 2. SERVE & DOCS WORKFLOW
        // ==========================================
        stage('Deploy and Document') {
            when {
                branch 'main'
                not { changeRequest() } 
            }
            steps {
                echo "Push to main detected. Deploying application and updating docs..."
                
                sh '''
                    LATEST_RUN_ID=$(python3 -c "import mlflow; from madewithml.config import MLFLOW_TRACKING_URI; mlflow.set_tracking_uri(MLFLOW_TRACKING_URI); runs=mlflow.search_runs(); print(runs.iloc[0].run_id if not runs.empty else '')")
                    
                    if [ -z "$LATEST_RUN_ID" ]; then
                        echo "Error: No MLflow runs found. You must train a model first!"
                        exit 1
                    fi
                    
                    echo "Found Run ID: $LATEST_RUN_ID"
                    python3 madewithml/serve.py --run_id $LATEST_RUN_ID
                '''
                
                sh 'python3 -m mkdocs build'
            }
        }
    }
    
    post {
        success {
            echo "All workloads finished successfully!"
        }
        failure {
            echo "Pipeline failed. Check the logs for errors."
        }
    }
}
