#include <stdio.h>
#include "PyLib.ref.h"
int main(void)
{
    printf("STR %s\n", PyLib_Hello_str("Bob"));
    printf("JSON %s\n", PyLib_Hello("\"Eve\""));
    printf("NUM %g\n", PyLib_Mul_num(6, 7));
    printf("MULJ %s\n", PyLib_Mul("2", "\"ab\""));
    return 0;
}
