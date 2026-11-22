// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Sales Chart - a bar chart drawn with Panels, in C# (RAD IDE GUI Bridge; Build > Publish = WinForms exe).
//
// Each bar is a Panel whose Top / Height follow its value (0..100). Shows: MouseDown with coordinates (click
// in the chart to set the bar under the mouse), a Timer animation whose speed comes from a TrackBar, the
// ColorDialog, NumericUpDown + ComboBox, saving / loading CSV with File.ReadAllLines, LINQ statistics.
using System;
using System.Globalization;
using System.IO;
using System.Linq;

public static partial class frmChart
{
    const int Bars = 6, Base = 280, BarW = 44, FirstX = 14, StepX = 60;
    const double Scale = 2.4;                       // pixels per unit: 100 -> 240 px
    static readonly string[] Months = { "Jan", "Feb", "Mar", "Apr", "May", "Jun" };
    static readonly double[] values = { 50, 65, 40, 80, 70, 90 };
    static readonly double[] drawn = new double[Bars];
    static readonly Random rnd = new Random();
    static string barColor = "#3B7DD8";

    static RadControl Bar(int i) => new RadControl($"frmChart.pnlBar{i + 1}");
    static RadControl ValueLabel(int i) => new RadControl($"frmChart.lblVal{i + 1}");

    static void DrawBar(int i)
    {
        int h = Math.Max(1, (int)Math.Round(drawn[i] * Scale));
        Bar(i).Top = Base - h;
        Bar(i).Height = h;
        ValueLabel(i).Top = Base - h - 20;
        ValueLabel(i).Caption = Math.Round(drawn[i]).ToString(CultureInfo.InvariantCulture);
    }

    static void UpdateStats()
    {
        int best = Array.IndexOf(values, values.Max());
        lblStats.Caption = $"Total: {values.Sum()}   Average: {values.Average():0.0}   " +
                           $"Best month: {Months[best]} ({values[best]})";
    }

    static void Redraw()
    {
        UpdateStats();
        if (chkAnimate.Value == "1")
        {
            tmrAnim.Enabled = true;         // tmrAnim_Tick moves the bars
            return;
        }
        for (int i = 0; i < Bars; i++)
        {
            drawn[i] = values[i];
            DrawBar(i);
        }
    }

    static void SetValue(int i, double v)
    {
        values[i] = Math.Round(Math.Max(0, Math.Min(100, v)));
        cboMonth.ListIndex = i;
        nudValue.Value = values[i].ToString(CultureInfo.InvariantCulture);
        Redraw();
    }

    // ------------------------------------------------------------------ events
    static void frmChart_Load(RadEvent e)
    {
        chkAnimate.Value = "1";
        cboMonth.ListIndex = 0;
        Redraw();
    }

    static void tmrAnim_Tick(RadEvent e)
    {
        double speed = Rad.ToNumber(trkSpeed.Value);
        bool moving = false;
        for (int i = 0; i < Bars; i++)
        {
            double d = values[i] - drawn[i];
            if (d == 0) continue;
            drawn[i] += Math.Max(-speed, Math.Min(speed, d));
            DrawBar(i);
            moving = true;
        }
        if (!moving) tmrAnim.Enabled = false;
    }

    static void btnSet_Click(RadEvent e)
    {
        if (cboMonth.ListIndex < 0) { MsgBox("Choose a month first."); return; }
        SetValue(cboMonth.ListIndex, Rad.ToNumber(nudValue.Value));
    }

    static void cboMonth_SelectedIndexChanged(RadEvent e)
    {
        int i = cboMonth.ListIndex;
        if (i >= 0) nudValue.Value = values[i].ToString(CultureInfo.InvariantCulture);
    }

    static void btnRandom_Click(RadEvent e)
    {
        for (int i = 0; i < Bars; i++) values[i] = rnd.Next(10, 101);
        Redraw();
    }

    static void btnColor_Click(RadEvent e)
    {
        dlgColor["Color"] = barColor;
        if (dlgColor.Call("ShowColor") != "OK") return;
        barColor = dlgColor["Color"];
        for (int i = 0; i < Bars; i++) Bar(i).BackColor = barColor;
    }

    // e.X / e.Y are relative to pnlChart: X picks the bar, Y the value
    static void pnlChart_MouseDown(RadEvent e)
    {
        int i = (e.X - FirstX + (StepX - BarW) / 2) / StepX;
        if (i >= 0 && i < Bars) SetValue(i, (Base - e.Y) / Scale);
    }

    static void btnSave_Click(RadEvent e)
    {
        try
        {
            File.WriteAllLines("sales.csv", new[] { "month,value" }
                .Concat(Months.Select((m, i) => $"{m},{values[i].ToString(CultureInfo.InvariantCulture)}")));
            MsgBox("Saved sales.csv");
        }
        catch (IOException ex) { MsgBox("Cannot write sales.csv: " + ex.Message); }
    }

    static void btnLoad_Click(RadEvent e)
    {
        if (!File.Exists("sales.csv")) { MsgBox("sales.csv not found - press Save first."); return; }
        foreach (var line in File.ReadAllLines("sales.csv").Skip(1))
        {
            var parts = line.Split(',');
            int i = Array.IndexOf(Months, parts[0]);
            if (i >= 0 && parts.Length > 1 && double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var v))
                values[i] = v;
        }
        Redraw();
    }

    static void chkAnimate_CheckedChanged(RadEvent e) => Redraw();
}
