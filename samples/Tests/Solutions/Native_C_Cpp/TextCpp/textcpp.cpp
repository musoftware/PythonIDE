// C++ library
#include <string>
#include "radgui.hpp"

namespace detail { int hidden(int x) { return x; } }

// Join two words
std::string Join(const std::string &a, const std::string &b) { return a + " " + b; }

/// Square a number
double Square(double x) { return x * x; }

static int priv() { return 1; }
inline int inl() { return 2; }

class Foo { public: int bar(int x) { return x; } };

extern "C" int CPlus(int a, int b) { return a + b; }
