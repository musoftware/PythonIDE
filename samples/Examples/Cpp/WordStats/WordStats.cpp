// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// WordStats - a console tool in C++: lines / words / characters of text files and the most frequent words.
//
//     WordStats [--top N] [--out report.txt] file1.txt [file2.txt ...]
//
// Without files it reads sample.txt next to the program (F5 in the IDE shows a result).
// Exit codes: 0 OK, 1 wrong arguments, 2 a file could not be read, 3 the report could not be written.
// Shows: a RAD IDE console project (no forms + a module with main), argument parsing, std::map /
// std::vector / std::sort, fstream, exceptions for bad numbers, exit codes.
#include <algorithm>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

struct Totals {
    long lines = 0, words = 0, chars = 0;
};

static bool count_file(const std::string &path, Totals &t, std::map<std::string, int> &freq, std::ostream &out)
{
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    Totals f;
    std::string line;
    while (std::getline(in, line)) {
        f.lines++;
        for (unsigned char c : line)
            if ((c & 0xC0) != 0x80 && c != '\r') f.chars++;          // UTF-8 characters, not bytes
        std::string word;
        for (size_t i = 0; i <= line.size(); i++) {
            unsigned char c = i < line.size() ? static_cast<unsigned char>(line[i]) : ' ';
            if (std::isalnum(c) || c >= 0x80 || c == '\'') {
                word += static_cast<char>(std::tolower(c));
            } else if (!word.empty()) {
                freq[word]++;
                f.words++;
                word.clear();
            }
        }
    }
    out << std::setw(8) << f.lines << std::setw(9) << f.words << std::setw(9) << f.chars << "  " << path << "\n";
    t.lines += f.lines;
    t.words += f.words;
    t.chars += f.chars;
    return true;
}

int main(int argc, char **argv)
{
    std::vector<std::string> files;
    std::string out_path;
    int top = 10;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "--help" || a == "-h") {
            std::cout << "usage: WordStats [--top N] [--out report.txt] file1.txt [file2.txt ...]\n";
            return 0;
        } else if (a == "--top" && i + 1 < argc) {
            try {
                top = std::stoi(argv[++i]);
            } catch (const std::exception &) {
                top = 0;
            }
            if (top <= 0) { std::cerr << "--top needs a positive number\n"; return 1; }
        } else if (a == "--out" && i + 1 < argc) {
            out_path = argv[++i];
        } else if (!a.empty() && a[0] == '-') {
            std::cerr << "unknown option " << a << "\n";
            return 1;
        } else {
            files.push_back(a);
        }
    }
    if (files.empty()) files.push_back("sample.txt");

    std::ofstream report;
    if (!out_path.empty()) {
        report.open(out_path);
        if (!report) { std::cerr << "cannot write " << out_path << "\n"; return 3; }
    }
    std::ostream &out = out_path.empty() ? std::cout : report;
    std::map<std::string, int> freq;
    Totals total;
    bool failed = false;
    out << "   lines    words    chars  file\n";
    for (const std::string &f : files)
        if (!count_file(f, total, freq, out)) {
            std::cerr << "cannot read " << f << "\n";
            failed = true;
        }
    if (files.size() > 1)
        out << std::setw(8) << total.lines << std::setw(9) << total.words << std::setw(9) << total.chars << "  total\n";

    std::vector<std::pair<std::string, int>> sorted(freq.begin(), freq.end());
    std::sort(sorted.begin(), sorted.end(), [](const auto &a, const auto &b) {
        return a.second != b.second ? a.second > b.second : a.first < b.first;
    });
    out << "\nTop " << top << " words:\n";
    for (int i = 0; i < top && i < (int)sorted.size(); i++)
        out << std::setw(4) << i + 1 << ". " << std::left << std::setw(20) << sorted[i].first << std::right << " "
            << sorted[i].second << "\n";
    if (!out_path.empty()) std::cout << "report written to " << out_path << "\n";
    return failed ? 2 : 0;
}
