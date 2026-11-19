# Class library RubyLib. Its module functions can be called from every project that
# references this library, in its own language, e.g.
#   Python: import RubyLib; RubyLib.Add(2, 3)     Ruby: require_relative "rubylib_ref"
module RubyLib
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
