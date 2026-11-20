# Class library RbLib. Its module functions can be called from every project that
# references this library, in its own language, e.g.
#   Python: import RbLib; RbLib.Add(2, 3)     Ruby: require_relative "rblib_ref"
module RbLib
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
