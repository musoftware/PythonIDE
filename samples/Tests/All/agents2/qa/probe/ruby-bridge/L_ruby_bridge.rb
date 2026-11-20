# Class library L_ruby_bridge. Its module functions can be called from every project that
# references this library, in its own language, e.g.
#   Python: import L_ruby_bridge; L_ruby_bridge.Add(2, 3)     Ruby: require_relative "l_ruby_bridge_ref"
module L_ruby_bridge
  module_function

  # Add two numbers.
  def Add(a, b)
    a + b
  end

  # Greeting text for who.
  def Greet(who)
    "Hello, #{who}!"
  end
end
