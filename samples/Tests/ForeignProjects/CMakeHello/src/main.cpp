#include <iostream>
#include "greet.h"

int main(int argc, char **argv)
{
    std::string who = argc > 1 && std::string(argv[1]) != "--test" ? argv[1] : "CMake";
    int total = add(2, 3);
    std::cout << greet(who) << " 2 + 3 = " << total << std::endl;
    return 0;
}
