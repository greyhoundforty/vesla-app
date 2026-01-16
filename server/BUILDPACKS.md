# Vesla Buildpacks - Language Detection & Auto-Containerization

Vesla automatically detects your application's language/framework and generates secure, production-ready Docker containers without requiring a Dockerfile.

## Supported Languages & Frameworks

### 🐍 Python
**Detection:** Presence of `requirements.txt`, `pyproject.toml`, `Pipfile`, or `setup.py`

**Supported Frameworks:**
- Flask
- Django
- FastAPI
- Gunicorn apps

**Auto-detected Entry Points:**
- `app.py` → `python app.py`
- `main.py` → `python main.py`
- `wsgi.py` → `gunicorn --bind 0.0.0.0:5000 wsgi:app`
- `manage.py` (Django) → `python manage.py runserver 0.0.0.0:8000`

**Base Image:** `python:3.11-slim`
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: myapp
domain: myapp.vesla-app.site
env:
  PORT: 5000
```

---

### 📦 Node.js
**Detection:** Presence of `package.json`

**Supported Frameworks:**
- Express
- Koa
- NestJS
- Next.js
- Any Node.js app

**Auto-detected Entry Points:**
- Checks `package.json` for `start` script
- Falls back to `index.js`, `server.js`, or `app.js`

**Base Image:** `node:20-slim`
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: node-api
domain: node-api.vesla-app.site
env:
  PORT: 3000
```

---

### 🔷 Go
**Detection:** Presence of `go.mod` or `main.go`

**Build Process:**
- Multi-stage build (compile → minimal runtime)
- Statically compiled binary (no dependencies)
- Final image based on `alpine:3.19`

**Base Image:** `golang:1.21-alpine` (builder) → `alpine:3.19` (runtime)
**Security:** Runs as non-root user `appuser` (uid 1000)
**Binary Size:** Extremely small final images (~10-20MB)

**Example vesla.yaml:**
```yaml
app: go-api
domain: go-api.vesla-app.site
env:
  PORT: 8080
```

---

### 🦀 Rust
**Detection:** Presence of `Cargo.toml`

**Build Process:**
- Multi-stage build with cargo
- Release-optimized binary
- Final image based on `debian:bookworm-slim`

**Base Image:** `rust:1.75-slim` (builder) → `debian:bookworm-slim` (runtime)
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: rust-api
domain: rust-api.vesla-app.site
env:
  PORT: 8000
```

---

### 💎 Ruby
**Detection:** Presence of `Gemfile` or `config.ru`

**Supported Frameworks:**
- Rails
- Sinatra
- Rack apps

**Auto-detected Entry Points:**
- `config.ru` (Rack) → `bundle exec rackup -o 0.0.0.0`
- Rails → `bundle exec rails server -b 0.0.0.0`
- `app.rb` (Sinatra) → `bundle exec ruby app.rb -o 0.0.0.0`

**Base Image:** `ruby:3.2-slim`
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: rails-app
domain: rails-app.vesla-app.site
env:
  PORT: 3000
```

---

### 🐘 PHP
**Detection:** Presence of `composer.json` or `index.php`

**Runtime:** PHP-FPM 8.2 with Nginx

**Supported Frameworks:**
- Laravel
- Symfony
- Plain PHP apps

**Base Image:** `php:8.2-fpm-alpine`
**Security:** PHP-FPM runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: php-app
domain: php-app.vesla-app.site
env:
  PORT: 9000
```

---

### ☕ Java (Maven)
**Detection:** Presence of `pom.xml`

**Build Process:**
- Multi-stage build with Maven
- Compiles to JAR file
- JRE-only runtime image

**Base Image:** `maven:3.9-eclipse-temurin-21-alpine` (builder) → `eclipse-temurin:21-jre-alpine` (runtime)
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: spring-api
domain: spring-api.vesla-app.site
env:
  PORT: 8080
```

---

### ☕ Java (Gradle)
**Detection:** Presence of `build.gradle` or `build.gradle.kts`

**Build Process:**
- Multi-stage build with Gradle
- Compiles to JAR file
- JRE-only runtime image

**Base Image:** `gradle:8.5-jdk21-alpine` (builder) → `eclipse-temurin:21-jre-alpine` (runtime)
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: spring-boot
domain: spring-boot.vesla-app.site
env:
  PORT: 8080
```

---

### 🔵 .NET
**Detection:** Presence of `*.csproj`, `*.fsproj`, or `*.vbproj` files

**Build Process:**
- Multi-stage build with .NET SDK
- Published to release output
- ASP.NET runtime image

**Base Image:** `mcr.microsoft.com/dotnet/sdk:8.0` (builder) → `mcr.microsoft.com/dotnet/aspnet:8.0-alpine` (runtime)
**Security:** Runs as non-root user `appuser` (uid 1000)

**Example vesla.yaml:**
```yaml
app: dotnet-api
domain: dotnet-api.vesla-app.site
env:
  PORT: 5000
```

---

### 📄 Static Sites
**Detection:** Presence of `index.html` (checked last)

**Runtime:** Nginx 1.25 (Alpine)

**Supported:**
- Plain HTML/CSS/JS
- React/Vue/Angular builds
- Static site generators (Hugo, Jekyll, etc.)

**Base Image:** `nginx:1.25-alpine`
**Security:** Runs as `nginx` user

**Example vesla.yaml:**
```yaml
app: static-site
domain: static-site.vesla-app.site
env:
  PORT: 80
```

---

## Custom Dockerfiles

If your app has a `Dockerfile`, Vesla will use it instead of auto-generating one. This gives you full control while still benefiting from Vesla's deployment automation.

**Example Project Structure:**
```
my-app/
├── Dockerfile          ← Vesla uses this
├── app.py
├── requirements.txt
└── vesla.yaml
```

---

## Security Features

All generated Dockerfiles follow security best practices:

### ✅ Non-Root Users
Every container runs as a non-root user (`appuser` with uid 1000), preventing privilege escalation attacks.

### ✅ Multi-Stage Builds
Compiled languages (Go, Rust, Java, .NET) use multi-stage builds:
- **Build stage:** Full SDK with build tools
- **Runtime stage:** Minimal image with only runtime dependencies
- **Result:** Smaller images with reduced attack surface

### ✅ Minimal Base Images
- Alpine Linux where possible (~5-10MB base)
- Slim variants for other languages
- Only necessary runtime dependencies installed

### ✅ Layer Caching
Dependencies are copied and installed before application code, maximizing Docker layer cache efficiency.

### ✅ No Unnecessary Tools
Build tools, compilers, and dev dependencies are not included in runtime images.

---

## Environment Variables

All runtimes support environment variables via `vesla.yaml`:

```yaml
app: myapp
domain: myapp.vesla-app.site
env:
  PORT: 8080
  DATABASE_URL: postgresql://user:pass@db:5432/mydb
  REDIS_URL: redis://redis:6379
  DEBUG: "false"
  API_KEY: "your-secret-key"
```

These are passed to the container at runtime and accessible in your application.

---

## Port Configuration

The `PORT` environment variable determines which port your app should listen on:

- **Python (Flask/FastAPI):** Default 5000
- **Node.js (Express):** Default 3000
- **Go:** Default 8080
- **Ruby (Rails):** Default 3000
- **Java (Spring Boot):** Default 8080
- **PHP:** Default 9000
- **.NET:** Default 5000
- **Static (Nginx):** Default 80

**Important:** Your application must listen on `0.0.0.0:<PORT>`, not `127.0.0.1`, to be accessible from outside the container.

---

## Runtime Detection Order

Vesla checks for files in this order:

1. **Dockerfile** (if present, use it)
2. **Go:** `go.mod` or `main.go`
3. **Rust:** `Cargo.toml`
4. **Python:** `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`
5. **Node.js:** `package.json`
6. **Ruby:** `Gemfile` or `config.ru`
7. **PHP:** `composer.json` or `index.php`
8. **Java (Maven):** `pom.xml`
9. **Java (Gradle):** `build.gradle` or `build.gradle.kts`
10. **.NET:** `*.csproj`, `*.fsproj`, `*.vbproj`
11. **Static:** `index.html`

If multiple indicators are present, the first match wins.

---

## Troubleshooting

### Build Fails with "Could not detect runtime"
- Ensure you have the correct dependency file (e.g., `requirements.txt` for Python)
- Check that the file is in the root of your project, not a subdirectory
- Provide a custom `Dockerfile` if using an unsupported language

### Container Starts but App Not Accessible
- Verify your app listens on `0.0.0.0:<PORT>`, not `127.0.0.1`
- Check the `PORT` environment variable matches your app's configuration
- Review container logs: `vesla logs <app-name>`

### Dependency Installation Fails
- Check your dependency file syntax (e.g., `requirements.txt`, `package.json`)
- Ensure all dependencies are publicly available
- Private dependencies may require custom Dockerfile with authentication

---

## Adding New Languages

To request support for additional languages or frameworks, open an issue in the Vesla repository with:

1. Language/framework name
2. Typical project structure (files to detect)
3. Build/run commands
4. Recommended base image

---

## Examples by Language

See the `/examples` directory for sample projects in each supported language:

```
examples/
├── python-flask/
├── node-express/
├── go-http/
├── rust-actix/
├── ruby-sinatra/
├── php-laravel/
├── java-spring/
├── dotnet-api/
└── static-react/
```

Each example includes:
- Application code
- Dependency files
- `vesla.yaml` configuration
- README with deployment instructions

---

## Best Practices

### 1. Pin Dependency Versions
Instead of:
```
flask
requests
```

Use:
```
flask==3.0.0
requests==2.31.0
```

### 2. Use .dockerignore
Create a `.dockerignore` file to exclude unnecessary files:
```
.git
.env
node_modules
__pycache__
*.pyc
.DS_Store
```

### 3. Health Checks
Add a `/health` endpoint for monitoring:
```python
@app.route('/health')
def health():
    return {'status': 'healthy'}
```

### 4. Graceful Shutdown
Handle SIGTERM signals properly to ensure clean container shutdowns.

### 5. Logging
Log to stdout/stderr, not files. Docker captures stdout/stderr automatically.

---

For more information, see the main Vesla documentation at `/opt/vesla/CLAUDE.md`.
