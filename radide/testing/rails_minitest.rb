# Test Explorer runner for Rails minitest suites (radide/testing/ruby_tests.py):
#   ruby <this file> [test/models/x_test.rb:12 ...]       (cwd = the Rails application)
# Runs `bin/rails test` in this process with an extra Minitest reporter that prints one
# "@@RADTEST@@{json}" line per test (id = "Class#test_name").
APP_PATH = File.expand_path("config/application", Dir.pwd)
require File.expand_path("config/boot", Dir.pwd)
require "json"
require "minitest"

module Minitest
  class RadIdeReporter < AbstractReporter
    def record(result)
      file, line = result.respond_to?(:source_location) ? result.source_location : [nil, nil]
      state = if result.skipped? then "skipped"
              elsif result.passed? then "passed"
              elsif result.error? then "error"
              else "failed"
              end
      msg = result.failures.map do |f|
        loc = f.respond_to?(:location) ? " [#{f.location}]" : ""
        "#{f.message}#{loc}"
      end.join("\n")
      klass = result.respond_to?(:klass) ? result.klass : result.class.name
      $stdout.puts "@@RADTEST@@" + JSON.generate({ "id" => "#{klass}##{result.name}", "name" => result.name,
                                                   "suite" => klass, "state" => state, "duration" => result.time,
                                                   "message" => msg, "file" => file.to_s, "line" => line.to_i })
      $stdout.flush
    end
  end

  def self.plugin_radide_init(_options)
    reporter << RadIdeReporter.new
  end
end
Minitest.extensions << "radide" unless Minitest.extensions.include?("radide")

ARGV.unshift("test")
require "rails/commands"
