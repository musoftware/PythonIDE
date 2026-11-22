# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# EntryStore - guestbook entries in a JSON file. A Mutex keeps parallel requests from losing writes;
# the file is written to a temporary name first and then renamed (no half-written file after a crash).
require "json"
require "fileutils"
require "time"

class EntryStore
  def initialize(path)
    @path = path
    @lock = Mutex.new
    FileUtils.mkdir_p(File.dirname(path))
  end

  def self.validate(form)
    errors = []
    errors << "Please type your name (2-40 characters)." unless (2..40).cover?(form["name"].to_s.length)
    errors << "Please type a message (up to 500 characters)." unless (1..500).cover?(form["message"].to_s.length)
    errors << "Choose a rating from 1 to 5." unless (1..5).cover?(form["rating"].to_i)
    errors
  end

  def all
    @lock.synchronize { read }
  end

  # newest first; q filters by name or message (case-insensitive)
  def search(q)
    list = all.sort_by { |e| -e["id"] }
    q = q.to_s.strip.downcase
    q.empty? ? list : list.select { |e| e["name"].downcase.include?(q) || e["message"].downcase.include?(q) }
  end

  def add(form)
    @lock.synchronize do
      list = read
      entry = { "id" => (list.map { |e| e["id"] }.max || 0) + 1, "name" => form["name"], "message" => form["message"],
                "rating" => form["rating"].to_i, "time" => Time.now.iso8601 }
      write(list << entry)
      entry
    end
  end

  def delete(id)
    @lock.synchronize { write(read.reject { |e| e["id"] == id }) }
  end

  private

  def read
    return [] unless File.exist?(@path)
    JSON.parse(File.read(@path, encoding: "UTF-8"))
  rescue JSON::ParserError
    []
  end

  def write(list)
    tmp = "#{@path}.tmp"
    File.write(tmp, JSON.pretty_generate(list), encoding: "UTF-8")
    File.rename(tmp, @path)
  end
end
