# Loaded with `ruby -r <this file> bin/rails server ...` by RAD IDE (F5 on a Rails or Sinatra web site).
# Opens the debug gem's remote port (RUBY_DEBUG_PORT / RUBY_DEBUG_HOST) without stopping the program; the IDE
# then speaks DAP to that port (radide/debug_more.py SocketDap). The app's own bundle is set up first so the
# debug gem of its Gemfile.lock is the one that is loaded.
ENV["BUNDLE_GEMFILE"] ||= File.join(Dir.pwd, "Gemfile")
begin
  require "bundler/setup" if File.exist?(ENV["BUNDLE_GEMFILE"])
rescue LoadError, StandardError => e
  warn "[radide] bundler/setup failed: #{e.message}"
end
begin
  require "debug/session"
  DEBUGGER__.open(nonstop: true)
  warn "[radide] debugger listening on #{ENV['RUBY_DEBUG_HOST']}:#{ENV['RUBY_DEBUG_PORT']} (debug #{DEBUGGER__::VERSION})"
rescue LoadError => e
  warn "[radide] the debug gem cannot be loaded (#{e.message}): add it to the Gemfile - " \
       "bundle add debug --group development - and press F5 again."
end
