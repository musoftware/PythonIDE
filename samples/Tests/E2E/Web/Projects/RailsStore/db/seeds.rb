# demo rows of a new database (bin/rails db:prepare / db:seed)
if Product.none?
  Product.create!(name: "Laptop", price: 999.5)
  Product.create!(name: "Phone", price: 450)
end
