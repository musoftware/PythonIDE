// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Star Catcher - an arcade game in C# (RAD IDE GUI Bridge; Build > Publish = native WinForms exe).
//
// Catch the yellow stars (+10), dodge the red rocks (-1 life); every 5 stars the game gets faster.
// Shows: a Timer game loop, KeyDown / KeyUp on the form (the key name in the IDE, the key code in the exe),
// MouseMove on a Panel (e.X), moving controls with Left / Top, rectangle collision (a small Sprite class),
// a best score kept in a file.
using System;
using System.IO;

public static partial class frmGame
{
    const int FieldW = 456, FieldH = 330;
    const string BestFile = "starcatcher.best";

    class Sprite
    {
        public string Path;           // "frmGame.lblStar" (names, not the designer fields: static fields of
                                      // partial classes in other files may not be set yet when these are made)
        public int X, Y, W, H;
        public bool Hits(Sprite o) => X < o.X + o.W && o.X < X + W && Y < o.Y + o.H && o.Y < Y + H;
        public void Draw() { Rad.Set(Path, "Left", X); Rad.Set(Path, "Top", Y); }
    }

    static readonly Sprite player = new Sprite { Path = "frmGame.pnlPlayer", X = 190, Y = 300, W = 76, H = 14 };
    static readonly Sprite star = new Sprite { Path = "frmGame.lblStar", X = 100, Y = -24, W = 24, H = 24 };
    static readonly Sprite rock = new Sprite { Path = "frmGame.lblRock", X = 300, Y = -24, W = 24, H = 24 };
    static readonly Random rnd = new Random();
    static int starSpeed, rockSpeed, score, lives, best;
    static bool leftKey, rightKey, running, paused;

    static void Drop(Sprite s, int extra) { s.X = rnd.Next(0, FieldW - s.W); s.Y = -s.H - rnd.Next(0, extra + 1); }

    static void ShowScore()
    {
        lblScore.Caption = $"Score: {score}";
        lblLives.Caption = $"Lives: {lives}";
        lblBest.Caption = $"Best: {best}";
    }

    static void Message(string text)
    {
        lblMessage.Caption = text;
        lblMessage.Visible = text != "";
    }

    static void GameOver()
    {
        running = false;
        tmrGame.Enabled = false;
        if (score > best)
        {
            best = score;
            try { File.WriteAllText(BestFile, best.ToString()); } catch (IOException) { }
            Message($"Game over - new best score {score}!");
        }
        else Message($"Game over - score {score}. Press Start.");
        ShowScore();
        btnStart.Caption = "Start";
    }

    // the key: its name ("Left") in the IDE's bridge, its Windows key code (37) in the WinForms exe
    static string Key(RadEvent e)
    {
        string[] a = e.Args.Split(' ');
        string k = a.Length > 3 ? a[3] : "";
        switch (k)
        {
            case "37": return "Left";
            case "39": return "Right";
            case "80": return "P";
            default: return k.ToUpperInvariant() == "P" ? "P" : k;
        }
    }

    // ------------------------------------------------------------------ events
    static void frmGame_Load(RadEvent e)
    {
        if (File.Exists(BestFile)) int.TryParse(File.ReadAllText(BestFile).Trim(), out best);
        ShowScore();
    }

    static void btnStart_Click(RadEvent e)
    {
        score = 0;
        lives = 3;
        starSpeed = 4;
        rockSpeed = 5;
        player.X = (FieldW - player.W) / 2;
        Drop(star, 0);
        Drop(rock, 200);
        running = true;
        paused = false;
        Message("");
        ShowScore();
        btnStart.Caption = "Restart";
        tmrGame.Enabled = true;
    }

    static void btnPause_Click(RadEvent e)
    {
        if (!running) return;
        paused = !paused;
        tmrGame.Enabled = !paused;
        btnPause.Caption = paused ? "Resume" : "Pause";
        Message(paused ? "Paused - press P or Resume" : "");
    }

    static void tmrGame_Tick(RadEvent e)
    {
        if (!running) return;
        player.X = Math.Max(0, Math.Min(FieldW - player.W, player.X + (rightKey ? 9 : 0) - (leftKey ? 9 : 0)));
        star.Y += starSpeed;
        rock.Y += rockSpeed;
        if (star.Hits(player))
        {
            score += 10;
            if (score % 50 == 0) { starSpeed++; rockSpeed++; }
            Drop(star, 0);
            ShowScore();
        }
        else if (star.Y > FieldH) Drop(star, 0);
        if (rock.Hits(player))
        {
            lives--;
            Drop(rock, 200);
            ShowScore();
            if (lives <= 0) { GameOver(); return; }
        }
        else if (rock.Y > FieldH) Drop(rock, 200);
        pnlPlayer.Left = player.X;
        star.Draw();
        rock.Draw();
    }

    static void frmGame_KeyDown(RadEvent e)
    {
        string k = Key(e);
        if (k == "Left") leftKey = true;
        else if (k == "Right") rightKey = true;
        else if (k == "P") btnPause_Click(e);
    }

    static void frmGame_KeyUp(RadEvent e)
    {
        string k = Key(e);
        if (k == "Left") leftKey = false;
        else if (k == "Right") rightKey = false;
    }

    static void pnlField_MouseMove(RadEvent e)
    {
        if (running && !paused) player.X = e.X - player.W / 2;
    }
}
