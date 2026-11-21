# The Rails console of RAD IDE's Rails panel: `ruby bin/rails runner <this file>` (the application is booted).
# One request per stdin line: a JSON string with the Ruby code. Each answer is one line:
#   "\u0001RADREPL" + JSON {"out": captured stdout/stderr, "result": inspect, "error": message, "class": ...}
# Local variables live on between requests (one binding), like irb.
require "json"
require "stringio"

begin
  require "rails/console/methods"
  include Rails::ConsoleMethods
rescue LoadError, NameError
end
begin
  Rails.application.load_console if Rails.application.respond_to?(:load_console)
rescue StandardError
end

module RadRepl
  class OutProxy
    def write(*args) = $stdout.write(*args)
    def <<(arg) = $stdout << arg
    def close; end
    def sync = true
    def sync=(_v); end
    def flush = self
  end

  def self.setup_logging
    return unless defined?(ActiveRecord::Base)
    ActiveRecord::Base.logger = ActiveSupport::Logger.new(OutProxy.new)
  rescue StandardError
  end
end

RadRepl.setup_logging
RAD_BINDING = binding
STDOUT.sync = true
real_out = STDOUT
real_out.puts "\u0001RADREPL" + JSON.generate({ "ready" => true, "rails" => Rails.version, "ruby" => RUBY_VERSION,
                                                 "env" => Rails.env })
while (line = STDIN.gets)
  begin
    code = JSON.parse(line)
  rescue JSON::ParserError
    code = line
  end
  buf = StringIO.new
  $stdout = buf
  $stderr = buf
  answer = {}
  begin
    value = eval(code.to_s, RAD_BINDING, "(rails console)", 1)
    answer["result"] = value.inspect.to_s[0, 20_000]
    answer["class"] = value.class.name
  rescue Exception => e # rubocop:disable Lint/RescueException
    raise if e.is_a?(SystemExit) && code.to_s.strip =~ /\A(exit|quit)\b/
    answer["error"] = "#{e.class}: #{e.message}"
    answer["backtrace"] = (e.backtrace || []).reject { |l| l.include?("rails_repl.rb") }.first(8)
  ensure
    $stdout = real_out
    $stderr = STDERR
  end
  answer["out"] = buf.string[0, 50_000]
  real_out.puts "\u0001RADREPL" + JSON.generate(answer)
end
