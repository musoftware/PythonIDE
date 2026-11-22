# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# ResultScreen - shows the score sent by MainScreen (self.FormArgs) and the list of answers.
from ResultScreen_designer import ResultScreenDesigner, RadEvent  # noqa: F401


class ResultScreen(ResultScreenDesigner):
    def ResultScreen_Load(self):
        args = self.FormArgs or {}
        score, total = args.get("score", 0), args.get("total", 0)
        stars = "*" * score
        self.lblResult.text = f"{score} / {total}  {stars}"
        self.lstAnswers.items = list(args.get("answers", []))
        print(f"RESULT {score}/{total}", flush=True)

    def btnAgain_Click(self):
        self.CloseForm("again")
