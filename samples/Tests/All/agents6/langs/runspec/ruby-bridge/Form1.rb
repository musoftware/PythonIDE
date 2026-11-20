def Form1_Load(e)
  Rad.set("lblOut", "Caption", "hi")
  File.write("loaded.txt", Rad.get("lblOut", "Caption") + "|" + Rad.get("txtA", "Text"))
  Rad.quit
end

def cmdGo_Click(e)
end
