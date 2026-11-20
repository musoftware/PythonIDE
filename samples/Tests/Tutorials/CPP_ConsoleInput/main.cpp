#include <iostream>
#include <string>

int main()
{
    std::string firstWord;
    std::string fullLine;

    std::cout << "اكتب اسمك الكامل: ";
    std::cin >> firstWord;            // كلمة واحدة فقط
    std::getline(std::cin, fullLine); // باقي السطر

    std::cout << "الكلمة الأولى: " << firstWord << "\n";
    std::cout << "الباقي:" << fullLine << "\n";
    return 0;
}
