function Form1_Load(e)
  rad.set("lblOut", "Caption", "loaded")
end

function cmdGo_Click(e)
  local t = rad.get("txtA", "Text")
  local n = radcall("Helpers.add", 2, 3)
  local m = radcall("Helpers.add", n, 2)
  rad.set("lblOut", "Caption", t .. "|" .. tostring(n) .. "|" .. tostring(m))
  ui.lstLog:AddItem(t)
end

function cmdBoom_Click(e)
  error("boom on purpose")
end

function cmdErr_Click(e)
  local ok, err = pcall(radcall, "Helpers.nope")
  rad.set("lblErr", "Caption", ok and "noerror" or ("err " .. tostring(err)))
end
