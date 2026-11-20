module Helpers
  module_function

  def add(a, b)
    puts "logged add"
    a + b
  end

  def greet(w) = "Hello, #{w}"
  def info = { "a" => [1, 2], "s" => "x" }
  def fail = raise("bad thing")
end
