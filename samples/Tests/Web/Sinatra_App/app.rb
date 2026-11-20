# Sinatra1 - a Sinatra web application (pure Ruby: no compiler needed).
# Run it with F5 / Ctrl+F5 in RAD IDE: the IDE passes the port with -p.
require "bundler/setup"
require "sinatra"
require "json"

set :bind, "127.0.0.1"
set :views, File.join(__dir__, "views")
set :public_folder, File.join(__dir__, "public")

PRODUCTS = [
  { id: 1, name: "Keyboard", price: 25.0 },
  { id: 2, name: "Mouse", price: 12.5 },
  { id: 3, name: "Monitor", price: 180.0 },
]

get "/" do
  @title = "Sinatra1"
  erb :index
end

get "/products" do
  @products = PRODUCTS
  erb :products
end

get "/products/:id" do
  @product = PRODUCTS.find { |p| p[:id] == params[:id].to_i }
  halt 404, "No such product" unless @product
  erb :product
end

post "/products" do
  PRODUCTS << { id: PRODUCTS.size + 1, name: params[:name].to_s, price: params[:price].to_f }
  redirect "/products"
end

get "/api/products" do
  content_type :json
  PRODUCTS.to_json
end
