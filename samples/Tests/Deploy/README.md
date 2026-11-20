# Deploy test projects (Docker + cloud publish)

Small projects used to test **Tools > Docker** (Dockerfile / compose / Dev Container generators, Docker panel, lint)
and **Site > Publish > Cloud / Git / SSH** (Vercel, Netlify, GitHub Pages, Azure, AWS, Render, Railway, SSH).
Each folder already contains the files the generator produced (`Dockerfile`, `.dockerignore`, `compose.yaml`,
`.devcontainer/devcontainer.json`); all of them passed hadolint 2.12.0, `docker build --check`,
`docker compose config` and a real `docker build` + `docker run` + HTTP request.

| Folder | Detected as | What it shows | How to try it |
|---|---|---|---|
| [`FlaskApi`](FlaskApi/) | Python - Flask | gunicorn image (python:3.12-slim, non-root user), `/api/health` reports `container: true` | Tools > Docker > Docker Panel > Build, then Run (8000:8000) and open http://localhost:8000/api/health |
| [`FastApiService`](FastApiService/) | Python - FastAPI | uvicorn image | Build + Run 8000:8000, open http://localhost:8000/docs |
| [`DjangoSite`](DjangoSite/) | Python - Django | gunicorn + `collectstatic`, compose with a PostgreSQL 16 service | Docker panel > Compose Up, open http://localhost:8000/ |
| [`ExpressApi`](ExpressApi/) | Node.js (Express) | node:22-alpine, `npm install --omit=dev`, runs as user `node`; compose `watch` sync | Open the project, Docker panel > Compose Up, open http://localhost:3000/ |
| [`PhpSite`](PhpSite/) | PHP site (Apache) | php:8.3-apache + pdo_mysql + mod_rewrite + AllowOverride, writable `data/` for SQLite; compose with MariaDB 11 | Build + Run 8080:80, the page counts visits in SQLite |
| [`StaticSite`](StaticSite/) | Static HTML (nginx) | nginx:1.27-alpine image; also the test site for GitHub Pages / Netlify / Vercel / S3 | Site > Deploy to Cloud / Git / SSH... > New > GitHub Pages, Preview / Dry Run |
| [`AspNetMinimal`](AspNetMinimal/) | .NET - ASP.NET Core | `dotnet new web` project; multi-stage sdk:9.0 -> aspnet:9.0, port 8080, `USER $APP_UID` | Build + Run 8080:8080 |

Python folders have no `project.radproj` on purpose (the Python web project types are added by another feature):
open them with Tools > Docker > Generate... and choose the folder, or let File > Open create the project.
