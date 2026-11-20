def Form1_Load(e)
  Rad.set("lblOut", "Caption", "loaded")
end

def cmdGo_Click(e)
  t = Rad.get("txtA", "Text")
  n = radcall("Helpers.add", 2, 3)
  m = radcall("Helpers.add", n, 2)
  Rad.set("lblOut", "Caption", "#{t}|#{n}|#{m}")
  ui.lstLog.AddItem(t)
end

def cmdBoom_Click
  raise "boom on purpose"
end

def cmdErr_Click(e)
  radcall("Helpers.nope")
  Rad.set("lblErr", "Caption", "noerror")
rescue => ex
  Rad.set("lblErr", "Caption", "err #{ex.message}")
end
