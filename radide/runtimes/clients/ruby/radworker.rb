# RAD IDE - RAD Hub worker for Ruby modules.
#
#   ruby radworker.rb <module file>          (cwd = project folder)
#
# Loads the module and serves its functions over stdin/stdout (JSON lines):
#   stdin : {"id": 7, "func": "add", "args": [2, 3]}
#   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
# A function is looked up as a singleton method of the module named like the file
# (Helpers.rb -> Helpers.add, e.g. `module Helpers; module_function; def add...`),
# then as a top-level method. puts/print output goes to stderr so stdout stays clean.
require_relative "rad"

file = ARGV[0]
unless file
  STDERR.puts "usage: ruby radworker.rb <module file>"
  exit 2
end
stem = File.basename(file, File.extname(file))

Rad.worker = true
REPLY = STDOUT.dup
REPLY.set_encoding(Encoding::UTF_8) rescue nil
REPLY.sync = true
$stdout = STDERR                       # puts / print -> stderr

load_error = nil
begin
  TOPLEVEL_BINDING.eval(File.read(file, encoding: "UTF-8"), File.expand_path(file), 1)
rescue ScriptError, StandardError => e
  load_error = "error loading #{file}: #{e.class}: #{e.message}"
  STDERR.puts "[radworker] #{load_error}"
end

# module constants tried for a file stem: math_lib.rb -> math_lib, Math_lib, MathLib
def rad_module_names(stem)
  [stem, stem[0].to_s.upcase + stem[1..].to_s, stem.split(/[_\W]+/).map(&:capitalize).join].uniq
end

def rad_find_function(stem, name)
  rad_module_names(stem).each do |const|
    mod = begin
      Object.const_defined?(const) ? Object.const_get(const) : nil
    rescue NameError
      nil
    end
    next unless mod.is_a?(Module)
    real = mod.singleton_methods.find { |m| m.to_s == name } ||
           mod.singleton_methods.find { |m| m.to_s.casecmp?(name) }
    return mod.method(real) if real
  end
  main = TOPLEVEL_BINDING.receiver
  own = Object.private_instance_methods(false) + Object.public_instance_methods(false)
  real = own.find { |m| m.to_s == name } || own.find { |m| m.to_s.casecmp?(name) }
  real ? main.method(real) : nil
end

def rad_reply(msg)
  text = begin
    JSON.generate(msg)
  rescue StandardError => e
    JSON.generate({ "id" => msg["id"], "error" => "result is not JSON: #{e.message}" })
  end
  REPLY.write(text + "\n")
end

STDIN.each_line do |line|
  line = line.strip
  next if line.empty?
  req = (JSON.parse(line) rescue nil)
  unless req.is_a?(Hash)
    rad_reply({ "id" => nil, "error" => "bad request" })
    next
  end
  id = req["id"]
  if load_error
    rad_reply({ "id" => id, "error" => load_error })
    next
  end
  name = req["func"].to_s
  fn = rad_find_function(stem, name)
  unless fn
    rad_reply({ "id" => id, "error" => "#{stem} has no function '#{name}'" })
    next
  end
  args = req["args"].is_a?(Array) ? req["args"] : []
  begin
    rad_reply({ "id" => id, "result" => fn.call(*args) })
  rescue SystemExit
    raise
  rescue Exception => e # rubocop:disable Lint/RescueException - report every error to the caller
    rad_reply({ "id" => id, "error" => "#{e.class}: #{e.message}" })
  end
end
