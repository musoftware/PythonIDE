// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Star Catcher - an arcade game in Java (RAD IDE GUI Bridge; Build > Publish = native Swing exe).
//
// Catch the yellow stars (+10), dodge the red rocks (-1 life); every 5 stars the game gets faster.
// Shows: a Timer game loop, KeyDown / KeyUp on the form, MouseMove on a Panel (e.x), moving controls with
// Left / Top, rectangle collision (a small Sprite class), java.util.Random, a best score kept in a file.
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Random;

public class frmGame extends frmGameDesigner {
    static final int FIELD_W = 456, FIELD_H = 330;
    static final Path BEST_FILE = Paths.get("starcatcher.best");
    static final Random rnd = new Random();

    static class Sprite {
        final String path;              // "frmGame.lblStar"
        int x, y;
        final int w, h;

        Sprite(String path, int x, int y, int w, int h) { this.path = path; this.x = x; this.y = y; this.w = w; this.h = h; }

        boolean hits(Sprite o) { return x < o.x + o.w && o.x < x + w && y < o.y + o.h && o.y < y + h; }

        void draw() { set(path, "Left", x); set(path, "Top", y); }

        void drop(int extra) { x = rnd.nextInt(FIELD_W - w); y = -h - rnd.nextInt(extra + 1); }
    }

    static final Sprite player = new Sprite("frmGame.pnlPlayer", 190, 300, 76, 14);
    static final Sprite star = new Sprite("frmGame.lblStar", 100, -24, 24, 24);
    static final Sprite rock = new Sprite("frmGame.lblRock", 300, -24, 24, 24);
    static int starSpeed, rockSpeed, score, lives, best;
    static boolean leftKey, rightKey, running, paused;

    static void showScore() {
        lblScore.setCaption("Score: " + score);
        lblLives.setCaption("Lives: " + lives);
        lblBest.setCaption("Best: " + best);
    }

    static void message(String text) {
        lblMessage.setCaption(text);
        lblMessage.setVisible(!text.isEmpty());
    }

    static void gameOver() {
        running = false;
        tmrGame.setEnabled(false);
        if (score > best) {
            best = score;
            try {
                Files.write(BEST_FILE, String.valueOf(best).getBytes(StandardCharsets.UTF_8));
            } catch (IOException ignored) {
                // the best score is only a bonus
            }
            message("Game over - new best score " + score + "!");
        } else {
            message("Game over - score " + score + ". Press Start.");
        }
        showScore();
        btnStart.setCaption("Start");
    }

    /** The key: its name ("Left") in the IDE's bridge, its key code (37) in the Swing exe. */
    static String key(RadEvent e) {
        String[] a = e.args.split(" ");
        String k = a.length > 3 ? a[3] : "";
        switch (k) {
            case "37": return "Left";
            case "39": return "Right";
            case "80": case "p": return "P";
            default: return k;
        }
    }

    // ------------------------------------------------------------------ events
    static void frmGame_Load(RadEvent e) {
        try {
            if (Files.exists(BEST_FILE)) best = Integer.parseInt(new String(Files.readAllBytes(BEST_FILE), StandardCharsets.UTF_8).trim());
        } catch (IOException | NumberFormatException ex) {
            best = 0;
        }
        showScore();
    }

    static void btnStart_Click(RadEvent e) {
        score = 0;
        lives = 3;
        starSpeed = 4;
        rockSpeed = 5;
        player.x = (FIELD_W - player.w) / 2;
        star.drop(0);
        rock.drop(200);
        running = true;
        paused = false;
        message("");
        showScore();
        btnStart.setCaption("Restart");
        tmrGame.setEnabled(true);
    }

    static void btnPause_Click(RadEvent e) {
        if (!running) return;
        paused = !paused;
        tmrGame.setEnabled(!paused);
        btnPause.setCaption(paused ? "Resume" : "Pause");
        message(paused ? "Paused - press P or Resume" : "");
    }

    static void tmrGame_Tick(RadEvent e) {
        if (!running) return;
        player.x = Math.max(0, Math.min(FIELD_W - player.w, player.x + (rightKey ? 9 : 0) - (leftKey ? 9 : 0)));
        star.y += starSpeed;
        rock.y += rockSpeed;
        if (star.hits(player)) {
            score += 10;
            if (score % 50 == 0) { starSpeed++; rockSpeed++; }
            star.drop(0);
            showScore();
        } else if (star.y > FIELD_H) {
            star.drop(0);
        }
        if (rock.hits(player)) {
            lives--;
            rock.drop(200);
            showScore();
            if (lives <= 0) { gameOver(); return; }
        } else if (rock.y > FIELD_H) {
            rock.drop(200);
        }
        pnlPlayer.setLeft(player.x);
        star.draw();
        rock.draw();
    }

    static void frmGame_KeyDown(RadEvent e) {
        String k = key(e);
        if (k.equals("Left")) leftKey = true;
        else if (k.equals("Right")) rightKey = true;
        else if (k.equals("P")) btnPause_Click(e);
    }

    static void frmGame_KeyUp(RadEvent e) {
        String k = key(e);
        if (k.equals("Left")) leftKey = false;
        else if (k.equals("Right")) rightKey = false;
    }

    static void pnlField_MouseMove(RadEvent e) {
        if (running && !paused) player.x = e.x - player.w / 2;
    }
}
