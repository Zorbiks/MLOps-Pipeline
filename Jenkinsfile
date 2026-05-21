pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
        PYTHONPATH = "${WORKSPACE}"
        GITHUB_USERNAME = 'Zorbiks' 
        
        // Tells Ray Serve to wait up to 120 seconds for the proxy to start 
        // to prevent timeouts in slow Docker containers
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
                '''
            }
        }

        // =========================================
        // 1. WORKLOADS WORKFLOW (Pull Request)
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
                    python3 madewithml/train.py train-model \
                        --experiment-name "llm-classification" \
                        --dataset-loc "https://raw.githubusercontent.com/GokuMohandas/Made-With-ML/main/datasets/dataset.csv" \
                        --train-loop-config '{"dropout_p": 0.5, "lr": 1e-4, "lr_factor": 0.8, "lr_patience": 3, "num_epochs": 10, "batch_size": 256}' \
                        --num-workers 1 \
                        --cpu-per-worker 1 \
                        --gpu-per-worker 0
                '''
            }
        }
        

        // ==========================================
        // 2. SERVE & DOCS WORKFLOW (Push to main)
        // ==========================================
        stage('Deploy and Document') {
            when {
                branch 'main'
                not { changeRequest() } 
            }
            steps {
                echo "Push to main detected. Deploying application and updating docs..."
                
                // 1. Dynamically fetch the latest Run ID from MLflow using inline Python
                // 2. Pass that dynamic variable directly into serve.py
                sh '''
                    LATEST_RUN_ID=$(python3 -c "import mlflow; from madewithml.config import MLFLOW_TRACKING_URI; mlflow.set_tracking_uri(MLFLOW_TRACKING_URI); runs=mlflow.search_runs(); print(runs.iloc[0].run_id if not runs.empty else '')")
                    
                    if [ -z "$LATEST_RUN_ID" ]; then
                        echo "Error: No MLflow runs found. You must train a model first!"
                        exit 1
                    fi
                    
                    echo "Found Run ID: $LATEST_RUN_ID"
                    python3 madewithml/serve.py --run_id $LATEST_RUN_ID
                '''
                
                // Update documentation 
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