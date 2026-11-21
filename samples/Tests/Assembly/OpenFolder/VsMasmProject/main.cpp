// VsMasmProject - C++ calling a MASM function (add3.asm), the way Visual Studio projects mix C++ and assembly.
#include <cstdio>

extern "C" long long add3(long long a, long long b, long long c);

int main() {
    std::printf("add3(1, 2, 3) = %lld\n", add3(1, 2, 3));
    return 0;
}
