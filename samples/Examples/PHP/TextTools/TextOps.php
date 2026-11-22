<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module TextOps - the operations of Text Tools. UTF-8 aware (mb_* and preg with /u), so Arabic works.

function apply_op(string $op, string $s): string
{
    switch ($op) {
        case 'UPPER CASE':
            return mb_strtoupper($s, 'UTF-8');
        case 'lower case':
            return mb_strtolower($s, 'UTF-8');
        case 'Title Case':
            return mb_convert_case($s, MB_CASE_TITLE, 'UTF-8');
        case 'Reverse':
            return implode('', array_reverse(mb_str_split($s, 1, 'UTF-8')));
        case 'Word count':
            $w = word_list($s);
            $freq = array_count_values(array_map(fn($x) => mb_strtolower($x, 'UTF-8'), $w));
            arsort($freq);
            $out = count($w) . " words\n";
            foreach (array_slice($freq, 0, 10, true) as $word => $n) {
                $out .= "$word: $n\n";
            }
            return rtrim($out);
        case 'Remove extra spaces':
            return implode("\n", array_map(fn($l) => trim(preg_replace('/\s+/u', ' ', $l)), explode("\n", $s)));
        case 'Slug':
            $slug = mb_strtolower(trim(preg_replace('/[^\p{L}\p{N}]+/u', '-', $s), '-'), 'UTF-8');
            return $slug;
        case 'Base64 encode':
            return base64_encode($s);
        case 'Base64 decode':
            $d = base64_decode(trim($s), true);
            if ($d === false) {
                throw new InvalidArgumentException('The input is not valid Base64.');
            }
            return $d;
        case 'MD5':
            return md5($s);
        case 'SHA-256':
            return hash('sha256', $s);
        case 'Sort lines':
            $lines = explode("\n", $s);
            sort($lines, SORT_STRING | SORT_FLAG_CASE);
            return implode("\n", $lines);
        case 'Unique lines':
            return implode("\n", array_values(array_unique(explode("\n", $s))));
        default:
            throw new InvalidArgumentException("Unknown operation: $op");
    }
}

function word_list(string $s): array
{
    preg_match_all('/[\p{L}\p{N}\']+/u', $s, $m);
    return $m[0];
}

function text_stats(string $s): array
{
    return ['chars' => mb_strlen($s, 'UTF-8'), 'words' => count(word_list($s)),
            'lines' => $s === '' ? 0 : substr_count($s, "\n") + 1, 'bytes' => strlen($s)];
}
