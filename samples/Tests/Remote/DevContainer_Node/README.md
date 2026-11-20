# Dev Container (Node 22)

What it shows: a folder with `.devcontainer/devcontainer.json` opened in a container. RAD IDE runs
`docker run` (bind mount at `/workspaces/DevContainer_Node`, env, port 3000 on 127.0.0.1), runs
`postCreateCommand`, then every terminal, Run, Build and Search runs inside it with `docker exec`; files are
edited directly through the bind mount.

How to try it (Docker Desktop must be running; the image `node:22-bookworm-slim` is pulled if missing):
1. File > Open Remote > Open Folder in Dev Container... and pick this folder. The confirmation lists the docker
   commands; Output shows their output.
2. Remote Explorer > Run: enter `node app.js` - Output prints `hello from the container, node v22...`.
3. Terminal button: a shell inside the container.
4. Right-click the top node > Stop Container (the container is also stopped when the IDE closes; remove it with
   `docker rm -f radide-dc-devcontainer_node-<hash>`).

Not automated: Docker Compose dev containers (`dockerComposeFile`) and Dev Container Features.
