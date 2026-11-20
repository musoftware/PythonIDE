require "colorize"
module Pk
  module_function
  def info
    "x".colorize(:red).uncolorize + String.instance_method(:colorize).owner.to_s
  end
end
