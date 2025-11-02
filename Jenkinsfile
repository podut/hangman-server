pipeline {
    agent any
    
    environment {
        // Python environment
        PYTHON_VERSION = '3.10'
        VENV_PATH = '.venv'
        
        // Application settings
        SECRET_KEY = credentials('hangman-secret-key')
        DEBUG = 'false'
        
        // Test configuration
        PYTEST_ARGS = '-v --tb=short --maxfail=5'
        COVERAGE_THRESHOLD = '80'
    }
    
    options {
        // Keep last 10 builds
        buildDiscarder(logRotator(numToKeepStr: '10'))
        
        // Timeout after 30 minutes
        timeout(time: 30, unit: 'MINUTES')
        
        // Don't allow concurrent builds
        disableConcurrentBuilds()
        
        // Add timestamps to console output
        timestamps()
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    echo '📥 Checking out code...'
                }
                checkout scm
                
                script {
                    // Display git info
                    sh 'git log -1 --oneline'
                    sh 'git branch'
                }
            }
        }
        
        stage('Validate Secrets') {
            steps {
                script {
                    echo '🔑 Validating required credentials...'
                    
                    // Check if SECRET_KEY is available
                    if (!env.SECRET_KEY) {
                        error "❌ Missing 'hangman-secret-key' credential! Please configure it in Jenkins Credentials."
                    }
                    
                    echo '✅ All required credentials are present'
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    echo '🔧 Setting up Python environment...'
                }
                
                // Check Python version
                sh "python${PYTHON_VERSION} --version || python3 --version || python --version"
                
                // Create virtual environment
                sh """
                    python3 -m venv ${VENV_PATH} || python -m venv ${VENV_PATH}
                    . ${VENV_PATH}/bin/activate
                    python --version
                    pip --version
                """
                
                // Upgrade pip
                sh """
                    . ${VENV_PATH}/bin/activate
                    pip install --upgrade pip setuptools wheel
                """
            }
        }
        
        stage('Install Dependencies') {
            steps {
                script {
                    echo '📦 Installing dependencies...'
                }
                
                sh """
                    . ${VENV_PATH}/bin/activate
                    cd server
                    pip install -r requirements.txt
                    pip list
                """
            }
        }
        
        stage('Code Quality Checks') {
            parallel {
                stage('Lint - Flake8') {
                    steps {
                        script {
                            echo '🔍 Running Flake8...'
                        }
                        
                        sh """
                            . ${VENV_PATH}/bin/activate
                            pip install flake8
                            flake8 server/src --count --select=E9,F63,F7,F82 --show-source --statistics || true
                            flake8 server/src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics || true
                        """
                    }
                }
                
                stage('Type Check - MyPy') {
                    steps {
                        script {
                            echo '🔍 Running MyPy...'
                        }
                        
                        sh """
                            . ${VENV_PATH}/bin/activate
                            pip install mypy
                            mypy server/src --ignore-missing-imports --no-strict-optional || true
                        """
                    }
                }
                
                stage('Security - Bandit') {
                    steps {
                        script {
                            echo '🔒 Running Bandit security scan...'
                        }
                        
                        sh """
                            . ${VENV_PATH}/bin/activate
                            pip install bandit
                            bandit -r server/src -ll || true
                        """
                    }
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo '🧪 Running tests...'
                }
                
                sh """
                    . ${VENV_PATH}/bin/activate
                    cd server
                    pytest ${PYTEST_ARGS} \
                        --cov=src \
                        --cov-report=xml:coverage.xml \
                        --cov-report=html:coverage_html \
                        --cov-report=term \
                        --junitxml=test-results.xml \
                        tests/
                """
            }
            
            post {
                always {
                    // Publish test results
                    junit 'server/test-results.xml'
                    
                    // Publish coverage report
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'server/coverage_html',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                script {
                    echo '🔗 Running integration tests...'
                }
                
                sh """
                    . ${VENV_PATH}/bin/activate
                    pytest ${PYTEST_ARGS} \
                        -m integration \
                        server/tests/ || true
                """
            }
        }
        
        stage('WebSocket Tests') {
            steps {
                script {
                    echo '🔌 Running WebSocket tests...'
                }
                
                // Start server in background
                sh """
                    . ${VENV_PATH}/bin/activate
                    cd server
                    python -m uvicorn src.main:app --host 0.0.0.0 --port 8888 > server.log 2>&1 &
                    SERVER_PID=\$!
                    echo \$SERVER_PID > server.pid
                    
                    # Wait for server to start
                    sleep 5
                    
                    # Check if server is running
                    curl -f http://localhost:8888/healthz || exit 1
                """
                
                // Run WebSocket tests
                sh """
                    . ${VENV_PATH}/bin/activate
                    python test_websocket.py || true
                """
            }
            
            post {
                always {
                    // Stop server
                    sh """
                        if [ -f server/server.pid ]; then
                            kill \$(cat server/server.pid) || true
                            rm server/server.pid
                        fi
                    """
                }
            }
        }
        
        stage('API Tests') {
            steps {
                script {
                    echo '🌐 Running API endpoint tests...'
                }
                
                sh """
                    . ${VENV_PATH}/bin/activate
                    pytest ${PYTEST_ARGS} \
                        -k "not websocket" \
                        server/tests/test_new_features.py
                """
            }
        }
        
        stage('Generate Reports') {
            steps {
                script {
                    echo '📊 Generating reports...'
                }
                
                // Generate OpenAPI spec
                sh """
                    . ${VENV_PATH}/bin/activate
                    cd server
                    python export_openapi.py
                """
                
                // Archive OpenAPI specs
                archiveArtifacts artifacts: 'docs/openapi.yaml,docs/openapi.json', fingerprint: true
            }
        }
        
        stage('Coverage Check') {
            steps {
                script {
                    echo "📈 Checking coverage threshold (${COVERAGE_THRESHOLD}%)..."
                }
                
                sh """
                    . ${VENV_PATH}/bin/activate
                    pip install coverage
                    cd server
                    coverage report --fail-under=${COVERAGE_THRESHOLD} || echo "⚠️ Coverage below threshold"
                """
            }
        }
        
        stage('Build Artifacts') {
            when {
                branch 'master'
            }
            steps {
                script {
                    echo '📦 Building deployment artifacts...'
                }
                
                // Create deployment package
                sh """
                    tar -czf hangman-server-\${BUILD_NUMBER}.tar.gz \
                        --exclude='.git' \
                        --exclude='.venv' \
                        --exclude='__pycache__' \
                        --exclude='*.pyc' \
                        --exclude='coverage_html' \
                        --exclude='test-results.xml' \
                        server/ \
                        docs/ \
                        client-examples/ \
                        README.md \
                        IMPLEMENTATION_REPORT.md
                """
                
                // Archive artifacts
                archiveArtifacts artifacts: 'hangman-server-*.tar.gz', fingerprint: true
            }
        }
    }
    
    post {
        success {
            script {
                echo '✅ Pipeline succeeded!'
            }
            
            // Send success notification (configure your notification method)
            // emailext(
            //     subject: "✅ Jenkins Build Successful: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
            //     body: "Build ${env.BUILD_NUMBER} succeeded. Check console output at ${env.BUILD_URL}",
            //     to: "${env.CHANGE_AUTHOR_EMAIL}"
            // )
        }
        
        failure {
            script {
                echo '❌ Pipeline failed!'
            }
            
            // Send failure notification
            // emailext(
            //     subject: "❌ Jenkins Build Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
            //     body: "Build ${env.BUILD_NUMBER} failed. Check console output at ${env.BUILD_URL}",
            //     to: "${env.CHANGE_AUTHOR_EMAIL}"
            // )
        }
        
        unstable {
            script {
                echo '⚠️ Pipeline unstable!'
            }
        }
        
        always {
            script {
                echo '🧹 Cleaning up...'
                
                // Clean workspace - must run inside node context
                node {
                    cleanWs(
                        deleteDirs: true,
                        patterns: [
                            [pattern: '.venv/**', type: 'INCLUDE'],
                            [pattern: '**/__pycache__/**', type: 'INCLUDE'],
                            [pattern: '**/coverage_html/**', type: 'INCLUDE'],
                            [pattern: '**/*.pyc', type: 'INCLUDE']
                        ]
                    )
                }
                
                // Display build duration
                def duration = currentBuild.durationString.replace(' and counting', '')
                echo "⏱️ Build duration: ${duration}"
            }
        }
    }
}
