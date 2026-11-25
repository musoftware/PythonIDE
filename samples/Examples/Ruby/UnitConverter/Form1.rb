# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Unit Converter - event handlers for Form1 (Ruby, GUI Bridge).
# Shows: ComboBoxes filled from code (SelectedIndexChanged reloads the unit lists), live conversion on
#        TextChanged, KeyPress (Enter adds to the history), swap, a ListBox history, menus, a module (Units.rb).
require_relative "Units"

def fill_units
  cat = ui.cboCategory.Text
  %w[cboFrom cboTo].each do |box|
    Rad.call(box, "Clear")
    Units.units(cat).each { |u| Rad.call(box, "AddItem", u) }
  end
  ui.cboFrom.ListIndex = 0
  ui.cboTo.ListIndex = 1
  convert
end

# Converts and shows the result; returns the text (nil when the input is not a number)
def convert
  cat, from, to = ui.cboCategory.Text, ui.cboFrom.Text, ui.cboTo.Text
  return if from.empty? || to.empty?
  text = ui.txtValue.Text.strip.tr(",", "")
  unless text.match?(/\A-?\d+(\.\d+)?\z/)
    ui.lblResult.Caption = "Type a number"
    return nil
  end
  value = text.to_f
  result = Units.convert(cat, value, from, to)
  line = "#{Units.format(value)} #{from} = #{Units.format(result)} #{to}"
  ui.lblResult.Caption = line
  line
rescue KeyError => e
  ui.lblResult.Caption = "Unknown unit: #{e.key}"
  nil
end

def Form1_Load(e)
  Rad.call("cboCategory", "Clear")
  Units.categories.each { |c| Rad.call("cboCategory", "AddItem", c) }
  ui.cboCategory.ListIndex = 0
  fill_units
end

def cboCategory_SelectedIndexChanged(e)
  fill_units
end

def cboFrom_SelectedIndexChanged(e)
  convert
end

def cboTo_SelectedIndexChanged(e)
  convert
end

def txtValue_TextChanged(e)
  convert
end

def cmdConvert_Click(e)
  line = convert
  Rad.call("lstHistory", "AddItem", line) if line
end

def txtValue_KeyPress(e)
  cmdConvert_Click(e) if e.args.split(" ")[3] == "13" || e.args.include?("Return")
end

def cmdSwap_Click(e)
  from, to = ui.cboFrom.ListIndex.to_i, ui.cboTo.ListIndex.to_i
  ui.cboFrom.ListIndex = to
  ui.cboTo.ListIndex = from
  convert
end

def mnuEditSwap_Click(e)
  cmdSwap_Click(e)
end

def mnuEditClear_Click(e)
  Rad.call("lstHistory", "Clear")
end

def mnuHelpAbout_Click(e)
  msgbox("Unit Converter - a RAD IDE example in Ruby. Length, mass, temperature, data and speed units.")
end
