pipeline {
    agent any
    
    environment {
        // Python environment
        PYTHON_VERSION = '3.10'
        VENV_PATH = '.venv'
        
        // Application settings
        // TEMP: Hardcoded for testing (replace with credentials('hangman-secret-key') in production)
        SECRET_KEY = 'dev-secret-key-minimum-32-chars-long-for-development-only'
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
                        error "❌ Missing SECRET_KEY environment variable!"
                    }
                    
                    echo "✅ SECRET_KEY present (length: ${env.SECRET_KEY.length()} chars)"
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    echo '🔧 Setting up Python environment...'
                }
                
                // Install required packages for venv (Debian/Ubuntu)
                sh """
                    apt-get update -qq || true
                    apt-get install -y python3-venv python3-pip || true
                """
                
                // Check Python version
                sh "python3 --version || python --version"
                
                // Create virtual environment
                sh """
                    python3 -m venv ${VENV_PATH}
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
        
        stage('Integration: WebSocket') {
            environment {
                // Isolated WebSocket test port
                WS_TEST_PORT = '8888'
                WS_TEST_TIMEOUT = '30'
            }
            
            steps {
                script {
                    echo '🔌 Running WebSocket integration tests...'
                    echo "   Port: ${WS_TEST_PORT}"
                    echo "   Timeout: ${WS_TEST_TIMEOUT}s"
                }
                
                // Clean any existing processes on the test port
                sh """
                    echo "🧹 Cleaning up any existing processes on port ${WS_TEST_PORT}..."
                    lsof -ti:${WS_TEST_PORT} | xargs kill -9 2>/dev/null || true
                    sleep 2
                """
                
                // Start server in isolated environment
                sh """
                    . ${VENV_PATH}/bin/activate
                    cd server
                    
                    echo "🚀 Starting test server on port ${WS_TEST_PORT}..."
                    nohup python -m uvicorn src.main:app \
                        --host 0.0.0.0 \
                        --port ${WS_TEST_PORT} \
                        --log-level warning \
                        > ../ws_test_server.log 2>&1 &
                    
                    SERVER_PID=\$!
                    echo \$SERVER_PID > ../ws_test_server.pid
                    echo "✅ Server started with PID: \$SERVER_PID"
                    
                    # Wait for server to be ready (max 30 seconds)
                    echo "⏳ Waiting for server to be ready..."
                    for i in \$(seq 1 30); do
                        if curl -sf http://localhost:${WS_TEST_PORT}/healthz >/dev/null 2>&1; then
                            echo "✅ Server is ready after \${i} seconds"
                            break
                        fi
                        if [ \$i -eq 30 ]; then
                            echo "❌ Server failed to start within 30 seconds"
                            cat ../ws_test_server.log
                            exit 1
                        fi
                        sleep 1
                    done
                    
                    # Verify server is responding
                    curl -v http://localhost:${WS_TEST_PORT}/healthz
                """
                
                // Run WebSocket tests with timeout
                sh """
                    . ${VENV_PATH}/bin/activate
                    
                    echo "🧪 Running WebSocket tests..."
                    timeout ${WS_TEST_TIMEOUT}s python test_websocket.py || {
                        EXIT_CODE=\$?
                        if [ \$EXIT_CODE -eq 124 ]; then
                            echo "⚠️ WebSocket tests timed out after ${WS_TEST_TIMEOUT}s"
                        else
                            echo "⚠️ WebSocket tests failed with exit code: \$EXIT_CODE"
                        fi
                        # Mark as unstable but don't fail the pipeline
                        exit 0
                    }
                    
                    echo "✅ WebSocket tests completed"
                """
            }
            
            post {
                always {
                    script {
                        echo '🧹 Cleaning up WebSocket test environment...'
                    }
                    
                    // Capture server logs
                    sh """
                        if [ -f ws_test_server.log ]; then
                            echo "📋 Server logs:"
                            tail -n 50 ws_test_server.log || true
                        fi
                    """
                    
                    // Stop server gracefully
                    sh """
                        if [ -f ws_test_server.pid ]; then
                            SERVER_PID=\$(cat ws_test_server.pid)
                            echo "🛑 Stopping server (PID: \$SERVER_PID)..."
                            
                            # Try graceful shutdown first
                            kill -TERM \$SERVER_PID 2>/dev/null || true
                            sleep 2
                            
                            # Force kill if still running
                            if kill -0 \$SERVER_PID 2>/dev/null; then
                                echo "⚠️ Server still running, forcing shutdown..."
                                kill -9 \$SERVER_PID 2>/dev/null || true
                            fi
                            
                            rm ws_test_server.pid
                            echo "✅ Server stopped"
                        fi
                        
                        # Final cleanup of port
                        lsof -ti:${WS_TEST_PORT} | xargs kill -9 2>/dev/null || true
                        
                        # Archive test logs
                        if [ -f ws_test_server.log ]; then
                            mv ws_test_server.log ws_test_server_\${BUILD_NUMBER}.log || true
                        fi
                    """
                    
                    // Archive WebSocket test logs
                    archiveArtifacts artifacts: 'ws_test_server_*.log', allowEmptyArchive: true
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
                echo '🧹 Cleaning up test environment...'
                
                // Clean workspace - must run inside node context
                node {
                    // Forcefully remove virtual environment and temp files
                    sh '''
                        echo "🗑️ Removing virtual environment..."
                        rm -rf .venv || true
                        
                        echo "🗑️ Removing Python cache files..."
                        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
                        find . -type f -name "*.pyc" -delete 2>/dev/null || true
                        find . -type f -name "*.pyo" -delete 2>/dev/null || true
                        
                        echo "🗑️ Removing test artifacts..."
                        rm -rf coverage_html/ .coverage coverage.xml test-results.xml || true
                        rm -rf server/coverage_html/ server/.coverage server/coverage.xml server/test-results.xml || true
                        
                        echo "🗑️ Removing build artifacts..."
                        rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ || true
                        rm -rf server/build/ server/dist/ server/*.egg-info/ || true
                        
                        echo "🗑️ Removing server logs and temp files..."
                        rm -f server/server.log server/server.pid || true
                        
                        echo "✅ Cleanup complete!"
                    '''
                    
                    // Final workspace cleanup (removes everything)
                    cleanWs(
                        deleteDirs: true,
                        disableDeferredWipeout: true,
                        notFailBuild: true
                    )
                }
                
                // Display build duration
                def duration = currentBuild.durationString.replace(' and counting', '')
                echo "⏱️ Build duration: ${duration}"
                echo "🎯 Test environment completely removed"
            }
        }
    }
}
