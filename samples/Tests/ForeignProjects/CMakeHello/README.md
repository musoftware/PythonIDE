# CMakeHello - foreign project test (CMake + MinGW)

Hand-written CMake project (a static library + an executable + a ctest test, plus a VS Code tasks.json).
Open `CMakeLists.txt` (or the folder) with File > Open: RAD IDE configures it with cmake + MinGW into its
own state folder (`%APPDATA%\RADIDE\foreign\...`, nothing is written here), lists the targets (`hello`),
builds and runs it with F5 / Ctrl+F5, and debugs it with gdb (breakpoints in `src/greet.cpp`).
The Native menu has Configure / Build all / Build <target> / Clean / ctest and the VS Code task.
