#include <iostream>
#include <string>
#include <vector>
#include "PyLib.ref.hpp"
#include "MathC.ref.hpp"
int main()
{
    std::string s = PyLib::Hello("Zed").str();
    double m = PyLib::Mul(6, 7);
    std::cout << "S " << s << "\n" << "M " << m << "\n";
    std::cout << "V " << PyLib::Mul(std::string("xy"), 3) << "\n";
    std::cout << "ADD " << (double)MathC::Add(1, 2.5) << "\n";
    std::cout << "EVEN " << MathC::IsEven(10).boolean() << "\n";
    try { PyLib::Mul("a", std::vector<int>{1}); } catch (const std::exception &e) { std::cout << "ERR " << e.what() << "\n"; }
    return 0;
}
