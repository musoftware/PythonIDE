from LoginForm import LoginForm  # show with: LoginForm(master=self.root)
    def mnuFileClear_Click(self):
        self.lstLog.delete(0, "end")
