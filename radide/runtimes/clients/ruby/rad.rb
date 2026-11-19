# RAD IDE - GUI Bridge client for Ruby (copied into the project when it runs).
#
# The IDE draws the forms; this program talks to it over stdin/stdout
# (protocol: docs/CONTRACTS.md section 1). Everything is synchronous.
#
#   Rad.set(obj, prop, value)          set a property     Rad.set("lblOut", "Caption", "Hi")
#   Rad.get(obj, prop)      -> String  read a property    Rad.get("txtA", "Text")
#   Rad.get_num(obj, prop)  -> Numeric read a property as a number
#   Rad.call(obj, method, *args)       call a method      Rad.call("lstLog", "AddItem", "line")
#   Rad.msgbox(text) / msgbox(text)    message box (waits for OK)
#   Rad.input(prompt)       -> String  input box
#   Rad.show(form) / Rad.hide(form)    show or hide a form
#   Rad.quit (or Rad.end)              quit the program
#   ui.txtA.Text, ui.lblOut.Caption = "x", ui.lstLog.AddItem("x")   property / method sugar
#   radcall("Module.func", *args) -> value
#        call a function of any project module, in any language, through the RAD Hub
#        (arguments and the result are JSON values)
# Handlers are methods named <Control>_<Event>; they get an optional RadEvent e
# (e.X, e.Y, e.Button, e.KeyCode, e.KeyChar, e.args).
require "json"
require "socket"

STDIN.set_encoding(Encoding::UTF_8) rescue nil
STDOUT.set_encoding(Encoding::UTF_8) rescue nil
STDOUT.sync = true
STDERR.sync = true

class RadEvent
  attr_reader :object, :event, :args, :X, :Y, :Button, :KeyCode, :KeyChar

  def initialize(object, event, args)
    @object, @event, @args = object, event, args
    p = args.split(" ", 5)
    num = lambda do |i|
      f = (p[i] || "0").to_f
      f == f.to_i ? f.to_i : f
    end
    @X, @Y, @Button, @KeyCode = num.call(0), num.call(1), num.call(2), num.call(3)
    @KeyChar = p[4] || ""
  end

  def to_s
    "RadEvent(#{@object}.#{@event} #{@args})"
  end
end

class RadCallError < StandardError; end

module Rad
  METHODS = %w[additem removeitem clear list setfocus move refresh zorder showdialog show hide start stop].freeze
  @worker = false   # true inside a RAD Hub worker: no IDE on stdin/stdout
  @out = STDOUT
  @hub = nil
  @hub_id = 0

  class << self
    attr_accessor :worker, :out

    def clean(v)
      v.to_s.gsub(/\r?\n/, " ")
    end

    def send_line(line)
      (@worker ? STDERR : @out).write(line + "\n")
    end

    def read_line
      return "" if @worker
      line = STDIN.gets
      exit(0) if line.nil?            # the IDE went away
      line.chomp
    end

    def set(obj, prop, value)
      send_line("SET #{obj} #{prop} #{clean(value)}")
      nil
    end

    def get(obj, prop)
      send_line("GET #{obj} #{prop}")
      read_line
    end

    def get_num(obj, prop)
      m = get(obj, prop).match(/\A\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?/)
      return 0 unless m
      f = m[0].to_f
      f == f.to_i ? f.to_i : f
    end

    def call(obj, method, *args)
      line = "CALL #{obj} #{method}"
      line += " " + args.map { |a| clean(a) }.join("\t") unless args.empty?
      send_line(line)
      read_line
    end

    def msgbox(text)
      send_line("MSGBOX #{clean(text)}")
      read_line
    end

    def input(prompt)
      send_line("INPUT #{clean(prompt)}")
      read_line
    end

    def show(form)
      send_line("SHOW #{form}")
    end

    def hide(form)
      send_line("HIDE #{form}")
    end

    def quit
      send_line("END")
      exit(0)
    end
    alias_method :end, :quit

    # ---------------------------------------------------------------- RAD Hub
    def radcall(name, *args)
      addr = ENV["RAD_HUB"].to_s
      raise RadCallError, "radcall(#{name}): RAD Hub is not running (RAD_HUB is not set)" if addr.empty?
      unless @hub
        host, _, port = addr.rpartition(":")
        begin
          @hub = TCPSocket.new(host, port.to_i)
          @hub.set_encoding(Encoding::UTF_8)
        rescue SystemCallError, SocketError => e
          raise RadCallError, "radcall(#{name}): cannot connect to RAD Hub at #{addr}: #{e.message}"
        end
      end
      id = (@hub_id += 1)
      @hub.write(JSON.generate({ "id" => id, "call" => name, "args" => args }) + "\n")
      @hub.flush
      loop do
        line = @hub.gets
        if line.nil?
          @hub = nil
          raise RadCallError, "radcall(#{name}): RAD Hub closed the connection"
        end
        line = line.strip
        next if line.empty?
        msg = (JSON.parse(line) rescue nil)
        next unless msg.is_a?(Hash) && msg["id"] == id
        raise RadCallError, "radcall(#{name}): #{msg['error']}" unless msg["error"].nil?
        return msg["result"]
      end
    end

    # ---------------------------------------------------------------- main loop
    def load_file(file)
      TOPLEVEL_BINDING.eval(File.read(file, encoding: "UTF-8"), File.expand_path(file), 1)
    rescue ScriptError, StandardError => e
      STDERR.puts "[Ruby] error in #{file}: #{e.class}: #{e.message}"
      STDERR.puts e.backtrace.first(5).join("\n") if e.backtrace
    end

    def find_handler(name)
      main = TOPLEVEL_BINDING.receiver
      candidates = Object.private_instance_methods + Object.instance_methods
      real = candidates.find { |m| m.to_s == name } || candidates.find { |m| m.to_s.casecmp?(name) }
      real ? main.method(real) : nil
    end

    def run
      while (line = STDIN.gets)
        line = line.chomp
        break if line == "QUIT"
        next unless line.start_with?("EVENT ")
        obj, ev, rest = line[6..].split(" ", 3)
        h = obj && ev ? find_handler("#{obj}_#{ev}") : nil
        if h
          begin
            h.arity.zero? ? h.call : h.call(RadEvent.new(obj, ev, rest.to_s))
          rescue SystemExit
            raise
          rescue Exception => e # rubocop:disable Lint/RescueException - report and keep running
            STDERR.puts "[Ruby] error in #{obj}_#{ev}: #{e.class}: #{e.message}"
            STDERR.puts e.backtrace.first(5).join("\n") if e.backtrace
          end
        end
        @out.write("DONE\n")
      end
      exit(0)
    end
  end

  # ui.<control>.<Prop> / ui.<control>.<Prop> = v / ui.<control>.<Method>(...)
  class Control < BasicObject
    def initialize(name)
      @name = name
    end

    def method_missing(sym, *args)
      n = sym.to_s
      if n.end_with?("=")
        ::Rad.set(@name, n[0..-2], args[0])
      elsif !args.empty? || METHODS.include?(n.downcase)
        ::Rad.call(@name, n, *args)
      else
        ::Rad.get(@name, n)
      end
    end

    def respond_to_missing?(*)
      true
    end
  end

  class UI < BasicObject
    def method_missing(sym, *_args)
      ::Rad::Control.new(sym.to_s)
    end

    def respond_to_missing?(*)
      true
    end
  end
end

def ui
  $__rad_ui ||= Rad::UI.new
end

def radcall(name, *args)
  Rad.radcall(name, *args)
end

def msgbox(text)
  Rad.msgbox(text)
end
