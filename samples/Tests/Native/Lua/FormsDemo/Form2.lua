-- Event handlers for Form2.
function Form2_Load(e)
  rad.set("txt2", "Text", "from Form2 Load")
end

function cmdClose2_Click(e)
  rad.set("Form1.lblOut", "Caption", rad.get("txt2", "Text"))
  rad.hide("Form2")
end
