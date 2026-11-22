# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# MainScreen - the quiz screen.  Shows: a multi-screen Kivy app designed in RAD IDE's phone designer,
# Button / Switch / ProgressBar / Timer controls, Toast and MsgBox dialogs, ShowForm(name, args) to open the
# result screen and Form_Closed to restart when it closes.
import random

from MainScreen_designer import MainScreenDesigner, RadEvent, run_app  # noqa: F401
from questions import QUESTIONS


class MainScreen(MainScreenDesigner):
    def MainScreen_Load(self):
        self.new_game()

    # ------------------------------------------------------------ game
    def new_game(self):
        self.order = list(range(len(QUESTIONS)))
        random.shuffle(self.order)
        self.index, self.score, self.answers = 0, 0, []
        self.pbProgress.max = len(self.order)
        self.show_question()

    def show_question(self):
        q = QUESTIONS[self.order[self.index]]
        self.current = q
        self.lblProgress.text = f"Question {self.index + 1} of {len(self.order)}"
        self.pbProgress.value = self.index
        self.lblQuestion.text = f"What is the capital of {q['country']}?"
        options = q["options"][:]
        random.shuffle(options)
        for btn, text in zip((self.btnA, self.btnB, self.btnC, self.btnD), options):
            btn.text = text
        self.lblScore.text = f"Score: {self.score}"
        self.seconds = 10
        self.tmrClock.enabled = self.swHard.active
        self.lblTime.text = "10 s left" if self.swHard.active else ""

    def answer(self, text):
        q = self.current
        ok = text == q["capital"]
        if ok:
            self.score += 1
            self.Toast("Correct!", 1)
        else:
            self.Toast(f"No - it is {q['capital']}", 1.5)
        self.answers.append(f"{'OK ' if ok else 'X  '} {q['country']}: {q['capital']}")
        print(f"ANSWER {q['country']} {text} {'ok' if ok else 'wrong'} score={self.score}", flush=True)
        self.index += 1
        if self.index >= len(self.order):
            self.tmrClock.enabled = False
            self.ShowForm("ResultScreen", {"score": self.score, "total": len(self.order), "answers": self.answers})
        else:
            self.show_question()

    # ------------------------------------------------------------ events
    def btnA_Click(self):
        self.answer(self.btnA.text)

    def btnB_Click(self):
        self.answer(self.btnB.text)

    def btnC_Click(self):
        self.answer(self.btnC.text)

    def btnD_Click(self):
        self.answer(self.btnD.text)

    def swHard_CheckedChanged(self, e=None):
        self.tmrClock.enabled = self.swHard.active
        self.seconds = 10
        self.lblTime.text = "10 s left" if self.swHard.active else ""

    def tmrClock_Tick(self):
        self.seconds -= 1
        self.lblTime.text = f"{self.seconds} s left"
        if self.seconds <= 0:
            self.answer("")                     # time is up = a wrong answer

    def AppBar1_Click(self, e):
        self.MsgBox("Pick the capital city of each country. Made with RAD IDE and Kivy.", "About")

    def Form_Closed(self, name, result):
        """The result screen was closed (Play again)."""
        self.new_game()


if __name__ == "__main__":
    run_app('MainScreen')
