# Jenkins CI/CD Setup pentru Hangman Server

Acest proiect include 3 variante de Jenkinsfile pentru diferite environment-uri.

## 📁 Fișiere Jenkins

| Fișier                | Descriere                     | Recomandat pentru         |
| --------------------- | ----------------------------- | ------------------------- |
| `Jenkinsfile`         | Pipeline complet pentru Linux | Production, Linux servers |
| `Jenkinsfile.windows` | Pipeline pentru Windows       | Development pe Windows    |
| `Jenkinsfile.docker`  | Pipeline cu Docker agent      | Containere, CI/CD modern  |

## 🚀 Quick Start

### 1. Configurare Jenkins Job

```groovy
// În Jenkins, creează un "Pipeline" job
// În secțiunea "Pipeline", selectează "Pipeline script from SCM"
// SCM: Git
// Repository URL: <your-repo-url>
// Script Path: Jenkinsfile (sau Jenkinsfile.windows)
```

### 2. Configurare Credentials

#### ⚠️ CRITIC: Configurare `hangman-secret-key`

**Pipeline-ul va eșua fără acest credential!** Eroarea va fi:

```
ERROR: hangman-secret-key
MissingContextVariableException: Required context class hudson.FilePath is missing
```

#### Pași pentru configurare:

1. **Accesează Jenkins Credentials**:

   ```
   Jenkins Dashboard → Manage Jenkins → Credentials → System → Global credentials (unrestricted)
   ```

2. **Adaugă Credential Nou**:

   - Click pe **"Add Credentials"**
   - Completează formularul:

   | Câmp            | Valoare                                                     |
   | --------------- | ----------------------------------------------------------- |
   | **Kind**        | Secret text                                                 |
   | **Scope**       | Global (Jenkins, nodes, items, all child items, etc)        |
   | **Secret**      | `<your-secret-key-value>` (ex: `my-super-secret-key-12345`) |
   | **ID**          | `hangman-secret-key` ⚠️ **EXACT acest ID!**                 |
   | **Description** | `Hangman Server SECRET_KEY for application`                 |

3. **Salvează**: Click pe **"OK"**

#### Generare SECRET_KEY securizat (opțional)

Dacă nu ai un secret key, generează unul securizat:

**Python:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**OpenSSL:**

```bash
openssl rand -base64 32
```

**PowerShell (Windows):**

```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

#### Verificare Credential

După creare, verifică că apare în listă:

```
Jenkins → Manage Jenkins → Credentials → System → Global credentials
```

Trebuie să vezi:

| ID                   | Name | Kind        | Description                  |
| -------------------- | ---- | ----------- | ---------------------------- |
| `hangman-secret-key` | -    | Secret text | Hangman Server SECRET_KEY... |

#### ✅ Validare Automată

Pipeline-ul include acum un stage **"Validate Secrets"** care va detecta imediat dacă credentialul lipsește:

```groovy
stage('Validate Secrets') {
    steps {
        script {
            if (!env.SECRET_KEY) {
                error "❌ Missing 'hangman-secret-key' credential!"
            }
            echo '✅ All required credentials are present'
        }
    }
}
```

Dacă credentialul lipsește, build-ul va eșua **devreme** (la stage 2), nu la final.

### 3. Plugin-uri Necesare

Instalează următoarele plugin-uri în Jenkins:

- **Pipeline** - Pipeline support
- **Git** - Git SCM support
- **JUnit** - Test results
- **HTML Publisher** - Coverage reports
- **Cobertura** sau **Coverage** - Coverage metrics
- **Workspace Cleanup** - Workspace management

## 📋 Pipeline Stages

### Jenkinsfile (Linux)

1. **Checkout** - Clone repository
2. **Setup Environment** - Create Python venv
3. **Install Dependencies** - Install requirements.txt
4. **Code Quality Checks** (parallel):
   - Flake8 (linting)
   - MyPy (type checking)
   - Bandit (security scan)
5. **Run Tests** - pytest with coverage
6. **Integration Tests** - Integration test suite
7. **WebSocket Tests** - Start server + test WebSocket
8. **API Tests** - Test REST endpoints
9. **Generate Reports** - OpenAPI export
10. **Coverage Check** - Verify 80% threshold
11. **Build Artifacts** - Create deployment package (master only)

### Jenkinsfile.windows (Windows)

1. **Checkout** - Clone repository
2. **Setup Environment** - Create venv (Windows)
3. **Install Dependencies** - pip install
4. **Run Tests** - pytest with coverage
5. **WebSocket Tests** - Test WebSocket functionality
6. **Generate OpenAPI** - Export OpenAPI specs

### Jenkinsfile.docker (Docker)

1. **Checkout** - Clone repository
2. **Install Dependencies** - pip install in container
3. **Run Tests** - pytest with coverage
4. **Coverage Report** - Display coverage

## 🧪 Test Execution

### Teste Automate

Pipeline-ul rulează automat:

- ✅ **Unit tests** - Toate testele din `server/tests/`
- ✅ **Integration tests** - Teste marcate cu `@pytest.mark.integration`
- ✅ **API tests** - Teste pentru endpoints (metrics, idempotency, OpenAPI, TLS)
- ✅ **WebSocket tests** - Test real cu server live

### Coverage Threshold

Pipeline-ul verifică că coverage-ul este **≥ 80%**.

Dacă e sub 80%, build-ul va fi marcat ca **UNSTABLE** (nu FAILED).

## 📊 Rapoarte Generate

### Test Results (JUnit)

- Format: XML
- Locație: `test-results.xml`
- Vizualizare: Jenkins Test Results

### Coverage Report (HTML)

- Format: HTML
- Locație: `coverage_html/index.html`
- Vizualizare: Jenkins HTML Publisher

### OpenAPI Specs

- Format: YAML + JSON
- Locație: `docs/openapi.yaml`, `docs/openapi.json`
- Arhivare: Jenkins Artifacts

## 🔧 Configurare Avansată

### Environment Variables

Poți adăuga variabile în Jenkinsfile:

```groovy
environment {
    SECRET_KEY = credentials('hangman-secret-key')
    DEBUG = 'false'
    SERVER_HOST = '0.0.0.0'
    SERVER_PORT = '8000'

    // Database (dacă folosești)
    DATABASE_URL = credentials('database-url')

    // Email notifications
    EMAIL_RECIPIENTS = 'dev-team@example.com'
}
```

### Post-Build Actions

#### Email Notifications

Decomentează în Jenkinsfile:

```groovy
post {
    success {
        emailext(
            subject: "✅ Build Successful: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: "Build succeeded. View: ${env.BUILD_URL}",
            to: "dev-team@example.com"
        )
    }

    failure {
        emailext(
            subject: "❌ Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: "Build failed. View: ${env.BUILD_URL}",
            to: "dev-team@example.com"
        )
    }
}
```

#### Slack Notifications

```groovy
post {
    always {
        slackSend(
            channel: '#builds',
            color: currentBuild.result == 'SUCCESS' ? 'good' : 'danger',
            message: "${env.JOB_NAME} #${env.BUILD_NUMBER}: ${currentBuild.result}\n${env.BUILD_URL}"
        )
    }
}
```

### Webhook Triggers

Configurează webhook în Git pentru auto-trigger:

1. Jenkins → Job → Configure
2. Build Triggers → "GitHub hook trigger for GITScm polling"
3. În GitHub: Settings → Webhooks → Add webhook
   - Payload URL: `http://jenkins-server/github-webhook/`
   - Content type: `application/json`
   - Events: `Push events`, `Pull requests`

## 🐳 Docker Agent (Recomandat)

### Avantaje

- ✅ Environment izolat și reproducibil
- ✅ Nu poluează Jenkins master cu dependințe
- ✅ Mai rapid decât setup manual
- ✅ Consistent între build-uri

### Dockerfile pentru Jenkins Agent

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-cov flake8 mypy bandit

CMD ["bash"]
```

Build și push:

```bash
docker build -t hangman-jenkins-agent:latest .
docker push your-registry/hangman-jenkins-agent:latest
```

Update Jenkinsfile.docker:

```groovy
agent {
    docker {
        image 'your-registry/hangman-jenkins-agent:latest'
    }
}
```

## 🔍 Troubleshooting

### ⚠️ ERORI CRITICE COMUNE

#### 1. MissingContextVariableException: Required context class hudson.FilePath is missing

**Simptom:**

```
hudson.model.MissingContextVariableException: Required context class hudson.FilePath is missing
Perhaps you forgot to surround the step with a step that provides this, such as: node
```

**Cauză**: `cleanWs()` rulează în afara unui context `node {}`

**Soluție**: ✅ **REZOLVAT** în toate Jenkinsfile-urile

```groovy
// ❌ GREȘIT
post {
    always {
        cleanWs()  // Nu are context node
    }
}

// ✅ CORECT
post {
    always {
        script {
            node {
                cleanWs()  // Rulează în context node
            }
        }
    }
}
```

#### 2. ERROR: hangman-secret-key

**Simptom:**

```
ERROR: hangman-secret-key
hudson.AbortException: No credentials found
```

**Cauză**: Credentialul `hangman-secret-key` nu există în Jenkins Credentials

**Soluție**: Creează credentialul (vezi secțiunea **"Configurare Credentials"** de mai sus)

**Verificare rapidă:**

```groovy
// Pipeline-ul include acum validare automată
stage('Validate Secrets') {
    steps {
        script {
            if (!env.SECRET_KEY) {
                error "❌ Missing 'hangman-secret-key' credential!"
            }
        }
    }
}
```

#### 3. Build eșuează la cleanup, dar testele sunt OK

**Simptom**: Toate stage-urile reușesc, dar build-ul eșuează în `post always`

**Cauză**: Combinația de:

- `cleanWs()` fără `node {}` context
- Credentialul lipsă blochează întregul pipeline

**Soluție**: ✅ **REZOLVAT** - ambele probleme fixate în commit-ul curent

### Build fails la "Setup Environment"

**Problema**: Python nu este găsit

**Soluție**:

```groovy
// Jenkinsfile
environment {
    PATH = "/usr/local/bin:/usr/bin:/bin:${env.PATH}"
    PYTHON_CMD = 'python3'
}
```

### WebSocket tests fail

**Problema**: Server nu pornește la timp

**Soluție**: Crește timeout-ul în Jenkinsfile:

```bash
# Wait for server (increase from 5 to 10 seconds)
sleep 10
```

### Coverage sub 80%

**Problema**: Coverage prea mic

**Soluție temporară**: Ajustează threshold:

```groovy
environment {
    COVERAGE_THRESHOLD = '70'  // Reduce temporarily
}
```

### Cleanup fails pe Windows

**Problema**: Files în uz nu pot fi șterse

**Soluție**: Adaugă retry:

```groovy
post {
    always {
        retry(3) {
            cleanWs()
        }
    }
}
```

## 📈 Best Practices

### 1. Branch Strategy

```groovy
stage('Deploy to Staging') {
    when {
        branch 'develop'
    }
    steps {
        // Deploy to staging
    }
}

stage('Deploy to Production') {
    when {
        branch 'master'
    }
    steps {
        // Deploy to production
    }
}
```

### 2. Manual Approval (Production)

```groovy
stage('Deploy to Production') {
    when {
        branch 'master'
    }
    steps {
        input message: 'Deploy to production?', ok: 'Deploy'

        // Deployment steps
    }
}
```

### 3. Parallel Execution

```groovy
stage('Tests') {
    parallel {
        stage('Unit Tests') {
            steps { /* ... */ }
        }
        stage('Integration Tests') {
            steps { /* ... */ }
        }
        stage('E2E Tests') {
            steps { /* ... */ }
        }
    }
}
```

### 4. Caching Dependencies

```groovy
stage('Install Dependencies') {
    steps {
        cache(maxCacheSize: 250, caches: [
            arbitraryFileCache(
                path: '.venv',
                cacheValidityDecidingFile: 'server/requirements.txt'
            )
        ]) {
            sh 'pip install -r server/requirements.txt'
        }
    }
}
```

## 🎯 Rezultate Așteptate

După configurare, fiecare build va:

1. ✅ Rula toate testele (16 teste pentru features noi + alte teste)
2. ✅ Genera coverage report (HTML + XML)
3. ✅ Verifica code quality (flake8, mypy, bandit)
4. ✅ Exporta OpenAPI specs
5. ✅ Crea deployment artifacts (pe master branch)
6. ✅ Trimite notificări (email/Slack)

**Build time tipic**: 5-10 minute

## 📞 Support

Pentru probleme cu Jenkins setup:

- Verifică Jenkins logs: `http://jenkins-server/log/all`
- Check build console output
- Contactează echipa DevOps

---

**Last Updated**: November 2, 2025
**Jenkins Version**: 2.4+ (LTS)
**Pipeline Version**: Declarative Pipeline
