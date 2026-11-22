Rails.application.routes.draw do
  resources :products
  get "login", to: "sessions#new"
  post "login", to: "sessions#create"
  delete "logout", to: "sessions#destroy"
  get "api/products", to: "products#api"
  get "up" => "rails/health#show", as: :rails_health_check
  root to: redirect("/index.html")
end
