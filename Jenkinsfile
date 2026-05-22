pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
        PYTHONPATH = "${WORKSPACE}"
        // Make sure your username is still set here!
        GITHUB_USERNAME = 'Zorbiks' 
        RAY_SERVE_PROXY_READY_CHECK_TIMEOUT_S = '120'
    }

    stages {
        // =========================================
        // 1. WORKLOADS WORKFLOW
        // =========================================
        stage('Model Development Workloads') {
            when {
                changeRequest()
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

                sh 'python3 -m pip install "click<8.1.0" "typer==0.9.0"'
                
                sh '''
                    # 1. MAGICAL FIX: Tell Jenkins NOT to kill our background processes!
                    export JENKINS_NODE_COOKIE=dontKillMe
                    
                    # 2. Get the latest Model Run ID
                    LATEST_RUN_ID=$(python3 -c "import mlflow; from madewithml.config import MLFLOW_TRACKING_URI; mlflow.set_tracking_uri(MLFLOW_TRACKING_URI); runs=mlflow.search_runs(experiment_names=['llm-classification']); print(runs.iloc[0].run_id if not runs.empty else '')")
                    
                    if [ -z "$LATEST_RUN_ID" ]; then
                        echo "Error: No MLflow runs found. You must train a model first!"
                        exit 1
                    fi
                    echo "Found Run ID: $LATEST_RUN_ID"
                    
                    # 3. Stop any existing deployed models to free up port 8000 and RAM
                    ray stop || true
                    
                    # 4. Deploy the new model in the background (nohup)
                    nohup python3 madewithml/serve.py --run_id $LATEST_RUN_ID > serve.log 2>&1 &
                    
                    # 5. Give the server a few seconds to boot up before finishing the pipeline
                    sleep 15
                '''
                
                // Build the documentation
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
