// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// WordStats - a console tool in Go: lines / words / characters of text files and the most frequent words.
//
//	WordStats [-top N] [-out report.txt] file1.txt [file2.txt ...]
//
// Without files it reads sample.txt next to the program (F5 in the IDE shows a result).
// Exit codes: 0 OK, 1 wrong arguments, 2 a file could not be read, 3 the report could not be written.
// Shows: a RAD IDE console project (no forms + a module with func main), the flag package, bufio.Scanner,
// maps + sort.Slice, io.Writer, os.Exit codes.
package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"os"
	"sort"
	"strings"
	"unicode"
	"unicode/utf8"
)

type totals struct{ lines, words, chars int }

func countFile(path string, freq map[string]int, out io.Writer) (totals, error) {
	var t totals
	f, err := os.Open(path)
	if err != nil {
		return t, err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimRight(sc.Text(), "\r")
		t.lines++
		t.chars += utf8.RuneCountInString(line)
		for _, w := range strings.FieldsFunc(strings.ToLower(line), func(r rune) bool {
			return !unicode.IsLetter(r) && !unicode.IsDigit(r) && r != '\''
		}) {
			freq[w]++
			t.words++
		}
	}
	fmt.Fprintf(out, "%8d %8d %8d  %s\n", t.lines, t.words, t.chars, path)
	return t, sc.Err()
}

func main() {
	top := flag.Int("top", 10, "how many frequent words to list")
	outPath := flag.String("out", "", "write the report to this file")
	flag.Usage = func() {
		fmt.Fprintln(os.Stderr, "usage: WordStats [-top N] [-out report.txt] file1.txt [file2.txt ...]")
	}
	// accept --top / --out too (the same options as the C, C++ and Rust versions)
	for i, a := range os.Args {
		if strings.HasPrefix(a, "--") {
			os.Args[i] = a[1:]
		}
	}
	flag.Parse()
	if *top <= 0 {
		fmt.Fprintln(os.Stderr, "-top needs a positive number")
		os.Exit(1)
	}
	files := flag.Args()
	if len(files) == 0 {
		files = []string{"sample.txt"}
	}
	var out io.Writer = os.Stdout
	if *outPath != "" {
		f, err := os.Create(*outPath)
		if err != nil {
			fmt.Fprintln(os.Stderr, "cannot write", *outPath)
			os.Exit(3)
		}
		defer f.Close()
		out = f
	}
	freq := map[string]int{}
	var all totals
	failed := false
	fmt.Fprintln(out, "   lines    words    chars  file")
	for _, path := range files {
		t, err := countFile(path, freq, out)
		if err != nil {
			fmt.Fprintln(os.Stderr, "cannot read", path)
			failed = true
			continue
		}
		all.lines, all.words, all.chars = all.lines+t.lines, all.words+t.words, all.chars+t.chars
	}
	if len(files) > 1 {
		fmt.Fprintf(out, "%8d %8d %8d  total\n", all.lines, all.words, all.chars)
	}
	words := make([]string, 0, len(freq))
	for w := range freq {
		words = append(words, w)
	}
	sort.Slice(words, func(i, j int) bool {
		if freq[words[i]] != freq[words[j]] {
			return freq[words[i]] > freq[words[j]]
		}
		return words[i] < words[j]
	})
	fmt.Fprintf(out, "\nTop %d words:\n", *top)
	for i := 0; i < *top && i < len(words); i++ {
		fmt.Fprintf(out, "%4d. %-20s %d\n", i+1, words[i], freq[words[i]])
	}
	if *outPath != "" {
		fmt.Println("report written to", *outPath)
	}
	if failed {
		os.Exit(2)
	}
}
