
// Pipeline - v1.0.0
pipeline {
    agent { label 'jenkins-jenkins-agent' }

    environment {
        IMAGE_NAME = "d4rkghost47/python-circuit-svc-1"
        REGISTRY = "https://index.docker.io/v1/"
        SHORT_SHA = "${GIT_COMMIT[0..7]}"
        RECIPIENTS = "reynosojose2005@gmail.com"
        GIT_MANIFESTS_REPO = "git@github.com:evil-cloud/resillience-poc-service-a-k8s.git"
        GIT_MANIFESTS_BRANCH = "main"
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                container('dind') {
                    script {
                        echo "🐳 Construyendo imagen con SHA: ${env.SHORT_SHA}"
                        sh """
                        docker build -t ${IMAGE_NAME}:${env.SHORT_SHA} .
                        docker tag ${IMAGE_NAME}:${env.SHORT_SHA} ${IMAGE_NAME}:latest
                        """
                    }
                }
            }
        }


        stage('Push Docker Image') {
            steps {
                container('dind') {
                    script {
                        withCredentials([string(credentialsId: 'docker-token', variable: 'DOCKER_TOKEN')]) {
                            sh """
                            echo "$DOCKER_TOKEN" | docker login -u "d4rkghost47" --password-stdin
                            docker push ${IMAGE_NAME}:${env.SHORT_SHA}
                            docker push ${IMAGE_NAME}:latest
                            """
                        }
                    }
                }
            }
        }




        stage('Update Helm/K8s Repo') {
            steps {
                script {
                    withCredentials([sshUserPrivateKey(credentialsId: 'github-ssh-key', keyFileVariable: 'SSH_KEY')]) {
                        sh """
                        echo "📂 Configurando ssh-agent para clonar el repositorio..."
                        eval \$(ssh-agent -s)
                        chmod 600 $SSH_KEY
                        ssh-add $SSH_KEY

                        echo "📂 Clonando repo de manifiestos..."
                        rm -rf service-a-k8s
                        GIT_SSH_COMMAND="ssh -i $SSH_KEY -o StrictHostKeyChecking=no" git clone ${GIT_MANIFESTS_REPO}
                        cd service-a-k8s

                        echo "✏️ Actualizando el values.yaml con la nueva imagen..."
                        sed -i "s|tag: .*|tag: ${env.SHORT_SHA}|g" values.yaml

                        echo "📤 Haciendo commit y push..."
                        git config user.email "ci-bot@example.com"
                        git config user.name "CI/CD Bot"
                        git add values.yaml
                        git commit -m "🚀 Actualizando imagen a ${env.SHORT_SHA}"
                        GIT_SSH_COMMAND="ssh -i $SSH_KEY -o StrictHostKeyChecking=no" git push --set-upstream origin ${GIT_MANIFESTS_BRANCH}
                        """
                    }
                }
            }
        }

    }
}