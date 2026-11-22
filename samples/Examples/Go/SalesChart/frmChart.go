// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Sales Chart - a bar chart drawn with Panels, in Go (RAD IDE GUI Bridge; Build > Publish makes an exe).
//
// Each bar is a Panel whose Top / Height follow its value (0..100). Shows: MouseDown with coordinates
// (e.X / e.Y: click in the chart to set the bar under the mouse), a Timer animation whose speed comes from a
// TrackBar, the ColorDialog, NumericUpDown + ComboBox, CSV with encoding/csv, statistics, math/rand.
package main

import (
	"encoding/csv"
	"fmt"
	"math"
	"math/rand"
	"os"
	"strconv"
)

const (
	bars   = 6
	base   = 280 // y of the bars' bottom inside pnlChart
	scale  = 2.4 // pixels per unit: 100 -> 240 px
	barW   = 44
	firstX = 14
	stepX  = 60
)

var (
	months   = [bars]string{"Jan", "Feb", "Mar", "Apr", "May", "Jun"}
	values   = [bars]float64{50, 65, 40, 80, 70, 90}
	drawn    [bars]float64
	barColor = "#3B7DD8"
)

func bar(i int) string      { return fmt.Sprintf("pnlBar%d", i+1) }
func valLabel(i int) string { return fmt.Sprintf("lblVal%d", i+1) }

func drawBar(i int) {
	h := int(math.Max(1, math.Round(drawn[i]*scale)))
	Set(bar(i), "Top", base-h)
	Set(bar(i), "Height", h)
	Set(valLabel(i), "Top", base-h-20)
	Set(valLabel(i), "Caption", int(math.Round(drawn[i])))
}

func updateStats() {
	total, best := 0.0, 0
	for i, v := range values {
		total += v
		if v > values[best] {
			best = i
		}
	}
	Set("lblStats", "Caption", fmt.Sprintf("Total: %g   Average: %.1f   Best month: %s (%g)",
		total, total/bars, months[best], values[best]))
}

func redraw() {
	updateStats()
	if GetNum("chkAnimate", "Value") == 1 {
		Set("tmrAnim", "Enabled", "True") // tmrAnim_Tick moves the bars
		return
	}
	for i := range values {
		drawn[i] = values[i]
		drawBar(i)
	}
}

func setValue(i int, v float64) {
	values[i] = math.Round(math.Max(0, math.Min(100, v)))
	Set("cboMonth", "ListIndex", i)
	Set("nudValue", "Value", values[i])
	redraw()
}

// ------------------------------------------------------------------ events
func frmChart_Load() {
	Set("chkAnimate", "Value", 1)
	Set("cboMonth", "ListIndex", 0)
	redraw()
}

func tmrAnim_Tick() {
	speed := GetNum("trkSpeed", "Value")
	moving := false
	for i := range values {
		d := values[i] - drawn[i]
		if d == 0 {
			continue
		}
		drawn[i] += math.Max(-speed, math.Min(speed, d))
		drawBar(i)
		moving = true
	}
	if !moving {
		Set("tmrAnim", "Enabled", "False")
	}
}

func btnSet_Click() {
	i := int(GetNum("cboMonth", "ListIndex"))
	if i < 0 {
		MsgBox("Choose a month first.")
		return
	}
	setValue(i, GetNum("nudValue", "Value"))
}

func cboMonth_SelectedIndexChanged() {
	if i := int(GetNum("cboMonth", "ListIndex")); i >= 0 && i < bars {
		Set("nudValue", "Value", values[i])
	}
}

func btnRandom_Click() {
	for i := range values {
		values[i] = float64(10 + rand.Intn(91))
	}
	redraw()
}

func btnColor_Click() {
	Set("dlgColor", "Color", barColor)
	if Call("dlgColor", "ShowColor") != "OK" {
		return
	}
	barColor = Get("dlgColor", "Color")
	for i := 0; i < bars; i++ {
		Set(bar(i), "BackColor", barColor)
	}
}

// e.X / e.Y are relative to pnlChart: X picks the bar, Y the value
func pnlChart_MouseDown(e RadEvent) {
	i := (e.X - firstX + (stepX-barW)/2) / stepX
	if i >= 0 && i < bars {
		setValue(i, float64(base-e.Y)/scale)
	}
}

func btnSave_Click() {
	f, err := os.Create("sales.csv")
	if err != nil {
		MsgBox("Cannot write sales.csv: " + err.Error())
		return
	}
	defer f.Close()
	w := csv.NewWriter(f)
	w.Write([]string{"month", "value"})
	for i, m := range months {
		w.Write([]string{m, strconv.FormatFloat(values[i], 'f', -1, 64)})
	}
	w.Flush()
	MsgBox("Saved sales.csv")
}

func btnLoad_Click() {
	f, err := os.Open("sales.csv")
	if err != nil {
		MsgBox("sales.csv not found - press Save first.")
		return
	}
	defer f.Close()
	rows, err := csv.NewReader(f).ReadAll()
	if err != nil {
		MsgBox("sales.csv is broken: " + err.Error())
		return
	}
	for _, r := range rows {
		for i, m := range months {
			if len(r) > 1 && r[0] == m {
				if v, err := strconv.ParseFloat(r[1], 64); err == nil {
					values[i] = v
				}
			}
		}
	}
	redraw()
}

func chkAnimate_CheckedChanged() { redraw() }
