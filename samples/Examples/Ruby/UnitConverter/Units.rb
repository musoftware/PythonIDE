# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module Units - conversion tables. Linear units are stored as "how many base units is one of this";
# temperature needs formulas (offsets), so it has its own to/from-Celsius lambdas.
module Units
  module_function

  LINEAR = {
    "Length" => { "Meter" => 1.0, "Kilometer" => 1000.0, "Centimeter" => 0.01, "Millimeter" => 0.001,
                  "Mile" => 1609.344, "Yard" => 0.9144, "Foot" => 0.3048, "Inch" => 0.0254 },
    "Mass" => { "Kilogram" => 1.0, "Gram" => 0.001, "Tonne" => 1000.0, "Pound" => 0.45359237, "Ounce" => 0.028349523125 },
    "Data" => { "Byte" => 1.0, "Kilobyte" => 1024.0, "Megabyte" => 1024.0**2, "Gigabyte" => 1024.0**3,
                "Terabyte" => 1024.0**4, "Bit" => 0.125 },
    "Speed" => { "m/s" => 1.0, "km/h" => 1000.0 / 3600, "mph" => 1609.344 / 3600, "knot" => 1852.0 / 3600 },
  }.freeze

  TEMPERATURE = {
    "Celsius" => [->(c) { c }, ->(c) { c }],
    "Fahrenheit" => [->(f) { (f - 32) * 5.0 / 9 }, ->(c) { c * 9.0 / 5 + 32 }],
    "Kelvin" => [->(k) { k - 273.15 }, ->(c) { c + 273.15 }],
  }.freeze

  def categories
    LINEAR.keys.take(2) + ["Temperature"] + LINEAR.keys.drop(2)
  end

  def units(category)
    category == "Temperature" ? TEMPERATURE.keys : LINEAR.fetch(category).keys
  end

  def convert(category, value, from, to)
    if category == "Temperature"
      TEMPERATURE.fetch(to)[1].call(TEMPERATURE.fetch(from)[0].call(value))
    else
      table = LINEAR.fetch(category)
      value * table.fetch(from) / table.fetch(to)
    end
  end

  # 1234.5 -> "1,234.5"; small numbers keep significant digits
  def format(x)
    return x.round(6).to_s if x.abs < 0.001 && x != 0
    s = format_number(x.round(6))
    s.sub(/\.0+\z/, "").sub(/(\.\d*?)0+\z/, '\1')
  end

  def format_number(x)
    int, frac = ("%.6f" % x).split(".")
    int = int.reverse.scan(/\d{1,3}/).join(",").reverse.then { |s| x.negative? ? "-#{s}" : s }
    "#{int}.#{frac}"
  end
end
