// Pipeline version: v1.1.2
pipeline {
    agent { label 'jenkins-jenkins-agent' }

    environment {
        IMAGE_NAME      = "d4rkghost47/python-circuit-svc-1"
        REGISTRY        = "https://index.docker.io/v1/"
        SHORT_SHA       = "${GIT_COMMIT[0..7]}"
        SONAR_PROJECT   = "python-circuit-svc-1"
        SONAR_HOST      = "http://sonarqube-sonarqube.sonarqube.svc.cluster.local:9000"
        TRIVY_HOST      = "http://trivy.trivy-system.svc.cluster.local:4954"
        TZ              = "America/Guatemala"
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    logInfo("CHECKOUT", "Starting code checkout...")
                    checkout scm
                    logSuccess("CHECKOUT", "Code checkout completed.")
                }
            }
        }

        stage('Static Code Analysis') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    script {
                        logInfo("ANALYSIS", "Running static code analysis with SonarQube...")
                        try {
                            sh '''
                            sonar-scanner \
                                -Dsonar.projectKey=${SONAR_PROJECT} \
                                -Dsonar.sources=app \
                                -Dsonar.host.url=${SONAR_HOST} \
                                -Dsonar.login=$SONAR_TOKEN
                            '''
                            logSuccess("ANALYSIS", "SonarQube analysis completed successfully.")
                        } catch (Exception e) {
                            logFailure("ANALYSIS", "SonarQube analysis failed: ${e.message}")
                            error("Stopping pipeline due to SonarQube failure.")
                        }
                    }
                }
            }
        }

        stage('Build Image') {
            steps {
                container('dind') {
                    script {
                        logInfo("BUILD", "Building Docker image...")
                        try {
                            sh '''
                            docker build --no-cache -t ${IMAGE_NAME}:${SHORT_SHA} .
                            docker tag ${IMAGE_NAME}:${SHORT_SHA} ${IMAGE_NAME}:latest
                            '''
                            logSuccess("BUILD", "Build completed.")
                        } catch (Exception e) {
                            logFailure("BUILD", "Docker build failed: ${e.message}")
                            error("Stopping pipeline due to build failure.")
                        }
                    }
                }
            }
        }

        stage('Push Image') {
            steps {
                container('dind') {
                    script {
                        withCredentials([string(credentialsId: 'docker-token', variable: 'DOCKER_TOKEN')]) {
                            logInfo("PUSH", "Uploading Docker image...")
                            try {
                                sh '''
                                echo "$DOCKER_TOKEN" | docker login -u "d4rkghost47" --password-stdin > /dev/null 2>&1
                                docker push ${IMAGE_NAME}:${SHORT_SHA}
                                docker push ${IMAGE_NAME}:latest
                                '''
                                logSuccess("PUSH", "Image pushed successfully.")
                            } catch (Exception e) {
                                logFailure("PUSH", "Docker push failed: ${e.message}")
                                error("Stopping pipeline due to push failure.")
                            }
                        }
                    }
                }
            }
        }

        stage('Security Scan') {
            steps {
                script {
                    logInfo("SECURITY SCAN", "Running Trivy security scan...")
                    try {
                        sh '''
                        trivy image --server ${TRIVY_HOST} ${IMAGE_NAME}:${SHORT_SHA} --severity HIGH,CRITICAL --quiet
                        '''
                        logSuccess("SECURITY SCAN", "Security scan completed successfully.")
                    } catch (Exception e) {
                        logFailure("SECURITY SCAN", "Trivy security scan failed: ${e.message}")
                        error("Stopping pipeline due to security scan failure.")
                    }
                }
            }
        }
    }

    post {
        success {
            logSuccess("PIPELINE", "Pipeline completed successfully.")
        }
        failure {
            logFailure("PIPELINE", "Pipeline failed.")
        }
    }
}

def logInfo(stage, message) {
    echo "[${stage}] [INFO] ${getTimestamp()} - ${message}"
}

def logSuccess(stage, message) {
    echo "[${stage}] [SUCCESS] ${getTimestamp()} - ${message}"
}

def logFailure(stage, message) {
    echo "[${stage}] [FAILURE] ${getTimestamp()} - ${message}"
}

def getTimestamp() {
    return sh(script: "TZ='America/Guatemala' date '+%Y-%m-%d %H:%M:%S'", returnStdout: true).trim()
}


