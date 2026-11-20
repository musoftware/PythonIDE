# Debugger test (Ruby): breakpoint on the "text = ..." line of cmdGreet_Click, then F5 and Greet.
$clicks = 0

def make_greeting(name, n)
  text = "Hello, #{name}! (click #{n})"
  text
end

def Form1_Load(e)
  Rad.set("lblOut", "Caption", "Press Greet.")
end

def cmdGreet_Click(e)
  name = Rad.get("txtName", "Text")
  $clicks += 1
  info = { name: name, clicks: $clicks, tags: %w[a b] }
  text = make_greeting(name, $clicks)
  Rad.set("lblOut", "Caption", text)
end
