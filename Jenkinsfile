// Pipeline - v1.0.2
pipeline {
    agent { label 'jenkins-jenkins-agent' }

    environment {
        IMAGE_NAME = "d4rkghost47/python-circuit-svc-1"
        REGISTRY = "https://index.docker.io/v1/"
        SHORT_SHA = "${GIT_COMMIT[0..7]}"
        RECIPIENTS = "reynosojose2005@gmail.com"
        GIT_MANIFESTS_REPO = "git@github.com:evil-cloud/resillience-poc-service-a-k8s.git"
        GIT_MANIFESTS_BRANCH = "main"
        GIT_MANIFESTS_REPO_NAME = "resillience-poc-service-a-k8s" // Repositorio sin prefijo de URL
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
                            echo "\$DOCKER_TOKEN" | docker login -u "d4rkghost47" --password-stdin
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
                        chmod 600 "\$SSH_KEY"
                        ssh-add "\$SSH_KEY"

                        echo "📂 Clonando repo de manifiestos..."
                        rm -rf "\$GIT_MANIFESTS_REPO_NAME"
                        GIT_SSH_COMMAND="ssh -i \$SSH_KEY -o StrictHostKeyChecking=no" git clone "\$GIT_MANIFESTS_REPO"

                        # Verificar si el directorio se creó correctamente
                        if [ -d "\$GIT_MANIFESTS_REPO_NAME" ]; then
                            cd "\$GIT_MANIFESTS_REPO_NAME"
                        else
                            echo "❌ ERROR: No se pudo clonar el repositorio. Abortando..."
                            exit 1
                        fi

                        echo "✏️ Antes de actualizar values.yaml:"
                        cat values.yaml

                        # Verificar si yq está instalado, si no, instalarlo
                        if ! command -v yq &> /dev/null; then
                            echo "🔧 'yq' no encontrado. Intentando instalar..."
                            if command -v wget &> /dev/null; then
                                echo "📥 Usando wget..."
                                wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
                            elif command -v curl &> /dev/null; then
                                echo "📥 Usando curl..."
                                curl -sL https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o /usr/local/bin/yq
                            else
                                echo "❌ ERROR: No se pudo instalar 'yq' porque ni wget ni curl están disponibles."
                                exit 1
                            fi
                            chmod +x /usr/local/bin/yq
                        fi

                        echo "✏️ Actualizando el values.yaml con la nueva imagen..."
                        yq e '.image.tag = "${env.SHORT_SHA}"' -i values.yaml

                        echo "✏️ Después de actualizar values.yaml:"
                        cat values.yaml

                        echo "📤 Haciendo commit y push..."
                        git config user.email "ci-bot@example.com"
                        git config user.name "CI/CD Bot"
                        git add values.yaml
                        git commit -m "🚀 Actualizando imagen a ${env.SHORT_SHA}" || echo "⚠️ No hay cambios en values.yaml, omitiendo commit."
                        GIT_SSH_COMMAND="ssh -i \$SSH_KEY -o StrictHostKeyChecking=no" git push --set-upstream origin "\$GIT_MANIFESTS_BRANCH"
                        """
                    }
                }
            }
        }
    }
}
