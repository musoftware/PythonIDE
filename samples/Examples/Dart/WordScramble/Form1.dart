// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Word Scramble - a small word game in Dart with a RAD IDE form (GUI Bridge).
// Shows: a Timer control (Tick every second), ProgressBar, reading a data file (words.txt) with dart:io,
// Random, string/list operations, game state kept between events, MsgBox at the end of the game.
import 'dart:io';
import 'dart:math';

import 'radgui.dart';

const gameSeconds = 60;
final _random = Random();
List<String> _words = [];
String _word = '';     // the word to find
int _score = 0;
int _left = gameSeconds;
int _hints = 0;        // letters revealed for the current word
bool _running = false;

void Form1_Load(RadEvent e) {
  _words = File('words.txt')
      .readAsLinesSync()
      .map((w) => w.trim().toLowerCase())
      .where((w) => w.length >= 3 && !w.startsWith('#'))
      .toList();
  _newGame();
}

void cmdNew_Click(RadEvent e) => _newGame();

void cmdCheck_Click(RadEvent e) {
  if (!_running) return;
  final guess = Rad.get('txtGuess', 'Text').trim().toLowerCase();
  if (guess.isEmpty) return;
  if (guess == _word) {
    _score += 10 - min(_hints * 3, 9);
    Rad.set('lblMessage', 'Caption', 'Correct! "$_word"');
    _nextWord();
  } else {
    Rad.set('lblMessage', 'Caption', 'Not "$guess" - try again.');
  }
  Rad.set('txtGuess', 'Text', '');
}

void txtGuess_KeyPress(RadEvent e) {
  if (e.keyCode == 13) cmdCheck_Click(e); // Enter
}

void cmdHint_Click(RadEvent e) {
  if (!_running || _hints >= _word.length - 1) return;
  _hints++;
  Rad.set('lblMessage', 'Caption', 'Starts with "${_word.substring(0, _hints)}"');
}

void cmdSkip_Click(RadEvent e) {
  if (!_running) return;
  Rad.set('lblMessage', 'Caption', 'It was "$_word".');
  _nextWord();
}

void Timer1_Tick(RadEvent e) {
  if (!_running) return;
  _left--;
  _showTime();
  if (_left <= 0) {
    _running = false;
    Rad.set('lblWord', 'Caption', _word.toUpperCase());
    Rad.set('cmdCheck', 'Enabled', 'False');
    Rad.msgbox('Time is up! Your score: $_score');
  }
}

// ------------------------------------------------------------------ game
void _newGame() {
  _score = 0;
  _left = gameSeconds;
  _running = true;
  Rad.set('cmdCheck', 'Enabled', 'True');
  Rad.set('lblMessage', 'Caption', 'Good luck!');
  _nextWord();
  _showTime();
}

void _nextWord() {
  _word = _words[_random.nextInt(_words.length)];
  _hints = 0;
  Rad.set('lblWord', 'Caption', scramble(_word).toUpperCase());
  Rad.set('lblScore', 'Caption', 'Score: $_score');
}

void _showTime() {
  Rad.set('lblTime', 'Caption', 'Time: $_left');
  Rad.set('prgTime', 'Value', max(_left, 0));
}

/// The letters of [word] in a random order (never the word itself when that is possible).
String scramble(String word) {
  final letters = word.split('');
  for (var tries = 0; tries < 10; tries++) {
    letters.shuffle(_random);
    if (letters.join() != word) break;
  }
  return letters.join();
}
