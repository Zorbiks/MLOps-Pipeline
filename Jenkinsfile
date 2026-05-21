pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
    }

    stages {
        // ==========================================
        // 0. ENVIRONMENT SETUP
        // ==========================================
        stage('Setup Python Venv') {
            steps {
                echo "Creating Python Virtual Environment..."
                // Create a venv named 'venv'
                sh 'python3 -m venv venv'
            }
        }

        // ==========================================
        // 1. WORKLOADS WORKFLOW (Pull Request)
        // ==========================================
        stage('Model Development Workloads') {
            when {
                changeRequest target: 'main'
            }
            steps {
                echo "Pull Request detected. Running model development workloads..."
                
                // Install dependencies into the venv
                sh './venv/bin/pip install -r requirements.txt'
                
                // Run training and evaluation using the venv's Python
                sh './venv/bin/python train.py'
                sh './venv/bin/python evaluate.py'
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
                
                sh './venv/bin/pip install -r requirements.txt'
                
                // Run the serving script
                sh './venv/bin/python serve.py'
                
                // Update documentation
                sh './venv/bin/mkdocs build'
            }
        }
    }
    
    post {
        always {
            // Clean up the virtual environment so it doesn't take up space
            sh 'rm -rf venv'
            echo "Pipeline execution complete. Cleaned up workspace."
        }
        success {
            echo "All workloads finished successfully!"
        }
        failure {
            echo "Pipeline failed. Check the logs for errors."
        }
    }
}