# VSCodeMultiRoot - foreign project test (VS Code multi-root workspace)

`Team.code-workspace` with three folders: `tools` (Python + tasks.json with dependsOn + launch.json with
preLaunchTask), `scripts` (Node launch config) and `../CMakeHello` (a CMake project - opened with the
CMake adapter). Open the .code-workspace: one solution with three projects; the launch configurations
are the run targets (Native > Startup target), the tasks are in the Native menu.
