#include <iostream>
#include "mathutil.h"

int main()
{
    for (int i = 1; i <= 3; ++i)
        std::cout << i << " squared = " << square(i) << std::endl;
    return 0;
}
