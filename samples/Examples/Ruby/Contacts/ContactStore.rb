# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module ContactStore - contacts kept in contacts.json (UTF-8, Arabic names are fine).
require "json"

module ContactStore
  module_function

  FILE = "contacts.json"
  Contact = Struct.new(:name, :phone, :email, :city, keyword_init: true)

  def all
    @all ||= load
  end

  def load
    return [] unless File.exist?(FILE)
    JSON.parse(File.read(FILE, encoding: "UTF-8")).map { |h| Contact.new(**h.transform_keys(&:to_sym)) }
  rescue JSON::ParserError
    []
  end

  def save
    File.write(FILE, JSON.pretty_generate(all.map(&:to_h)), encoding: "UTF-8")
  end

  # Returns an error message, or nil when the contact is valid.
  def validate(c)
    return "Please type a name." if c.name.to_s.strip.empty?
    return "The phone number may contain digits, spaces, + and - only." unless c.phone.to_s.match?(/\A[\d +\-]*\z/)
    return "The email address does not look right." unless c.email.to_s.empty? || c.email.match?(/\A[^@\s]+@[^@\s]+\.[^@\s]+\z/)
    nil
  end

  def add(c)
    all << c
    save
  end

  def update(index, c)
    all[index] = c
    save
  end

  def delete(index)
    all.delete_at(index)
    save
  end

  # [index, contact] pairs matching a search text (name, phone, email or city; case-insensitive)
  def search(text)
    t = text.to_s.strip.downcase
    all.each_with_index.select do |c, _i|
      t.empty? || c.to_h.values.any? { |v| v.to_s.downcase.include?(t) }
    end.map { |c, i| [i, c] }
  end

  def to_csv
    lines = ["Name,Phone,Email,City"]
    all.each { |c| lines << c.to_h.values.map { |v| v.to_s.include?(",") ? "\"#{v}\"" : v.to_s }.join(",") }
    lines.join("\n") + "\n"
  end
end
