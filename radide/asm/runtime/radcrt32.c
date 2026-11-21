/* RAD IDE GUI Bridge - C runtime glue for 32-bit assembly form programs (copied into the project).
 *
 * The MinGW-w64 toolchain of RAD IDE compiles 32-bit code (gcc -m32 -c) but has no 32-bit libraries, so a
 * 32-bit form program is linked with GNU ld straight against the system's ucrtbase.dll (SysWOW64). UCRT has
 * no exported printf / snprintf (the import libraries normally supply them as small wrappers around
 * __stdio_common_*): these are the same wrappers, used by radgui.c and radasm.c.
 */
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

int __cdecl snprintf(char *buf, size_t size, const char *fmt, ...)
{
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = __stdio_common_vsprintf(2 /* _CRT_INTERNAL_PRINTF_STANDARD_SNPRINTF_BEHAVIOR */, buf, size, fmt, NULL, ap);
    va_end(ap);
    return n;
}

int __cdecl printf(const char *fmt, ...)
{
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = __stdio_common_vfprintf(0, stdout, fmt, NULL, ap);
    va_end(ap);
    return n;
}
