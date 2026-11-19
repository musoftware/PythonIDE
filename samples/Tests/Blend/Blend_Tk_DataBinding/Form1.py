from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        import json as _j
        r, b, res = self.root, self.Button1, {}
        def s1():
            r.update(); res["items"] = list(self.ListBox1.get(0, "end")); res["bg0"] = str(b.cget("bg"))
            b.event_generate("<Enter>"); r.update()
            res["bg_hover"], res["text_hover"] = str(b.cget("bg")), b.cget("text")
            b.event_generate("<Leave>"); r.update(); res["bg_left"] = str(b.cget("bg"))
            self.Slide.Begin(); r.after(250, s2)
        def s2():
            res["mid"] = int(float(b.place_info()["x"])); res["playing"] = bool(self.Slide.IsPlaying); r.after(600, s3)
        def s3():
            res["end"] = int(float(b.place_info()["x"])); print("RESULT " + _j.dumps(res), flush=True); r.destroy()
        r.after(300, s1)


if __name__ == "__main__":
    Form1().show()
