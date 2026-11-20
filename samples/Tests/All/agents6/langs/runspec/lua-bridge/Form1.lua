function Form1_Load(e)
  rad.set("lblOut", "Caption", "hi")
  local f = io.open("loaded.txt", "w"); f:write(rad.get("lblOut", "Caption") .. "|" .. rad.get("txtA", "Text")); f:close()
  rad.quit()
end

function cmdGo_Click(e) end
