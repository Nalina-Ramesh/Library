pipeline {
    agent any

    environment {
        IMAGE_NAME = 'library-management-system'
        CONTAINER_NAME = 'lms-app'
    }

    stages {
        stage('Clone Repository') {
            steps {
                // If Jenkins job is connected to SCM, this checks out current branch.
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install --upgrade pip'
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Build Docker Image') {
            steps {
                bat 'docker build -t %IMAGE_NAME%:latest .'
            }
        }

        stage('Run Docker Container') {
            steps {
                bat 'docker rm -f %CONTAINER_NAME% || ver > nul'
                bat 'docker run -d --name %CONTAINER_NAME% -p 5000:5000 %IMAGE_NAME%:latest'
            }
        }
    }

    post {
        success {
            echo 'Pipeline executed successfully. App should be available at http://localhost:5000'
        }
        failure {
            echo 'Pipeline failed. Check stage logs for errors.'
        }
    }
}
