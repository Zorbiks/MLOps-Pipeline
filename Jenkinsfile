pipeline {
    agent any

    environment {
        // Ensures Python output is sent straight to the terminal without buffering
        PYTHONUNBUFFERED = '1'
        // Tells Python to treat the root workspace as a package directory
        PYTHONPATH = "${WORKSPACE}"
        // REQUIRED BY RAY: Add your GitHub username here
        GITHUB_USERNAME = 'Zorbiks' 
    }

    stages {
        // ==========================================
        // 0. ENVIRONMENT SETUP
        // ==========================================
        stage('Install Global Dependencies') {
            steps {
                echo 'Installing dependencies directly into the Docker container...'
                sh '''
                    # Upgrade pip and wheel, but PIN setuptools to <70.0.0 so Ray doesn't break
                    python3 -m pip install --upgrade pip wheel --root-user-action=ignore
                    python3 -m pip install "setuptools<70.0.0" --root-user-action=ignore
                    
                    # Install project requirements
                    python3 -m pip install --no-cache-dir -r requirements.txt --root-user-action=ignore
                '''
            }
        }

        // =========================================
        // 1. WORKLOADS WORKFLOW (Pull Request)
        // =========================================
        stage('Model Development Workloads') {
            when {
                changeRequest target: 'main'
            }
            steps {
                echo "Pull Request detected. Running model development workloads..."
                
                // Run directly from the root workspace using the folder path
                sh 'python3 madewithml/train.py'
                sh 'python3 madewithml/evaluate.py'
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
                
                // Run directly from the root workspace using the folder path
                sh 'python3 madewithml/serve.py'
                
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