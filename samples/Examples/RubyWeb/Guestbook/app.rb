# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Guestbook - a Sinatra web application (pure Ruby: sinatra + rackup + webrick, no C compiler needed).
# Shows: routes (GET/POST), ERB views with a layout, a form with server-side validation, a JSON file "database"
# (data/entries.json, safe for parallel requests with a Mutex), search, a JSON API, English / Arabic (RTL) pages.
# Run it with F5 / Ctrl+F5 in RAD IDE: the IDE installs the gems (bundle install) and passes the port with -p.
require "bundler/setup"
require "sinatra"
require "json"
require "time"
require_relative "lib/entry_store"

set :bind, "127.0.0.1"
set :views, File.join(__dir__, "views")
set :public_folder, File.join(__dir__, "public")
set :store, EntryStore.new(File.join(__dir__, "data", "entries.json"))

TEXTS = {
  "en" => { title: "Guestbook", lead: "Leave a message for the next visitor.", name: "Your name",
            message: "Message", rating: "Rating", send: "Sign the guestbook", search: "Search",
            empty: "No messages yet - be the first!", other: "العربية", count: "%d message(s)" },
  "ar" => { title: "سجل الزوار", lead: "اترك رسالة للزائر التالي.", name: "اسمك", message: "الرسالة",
            rating: "التقييم", send: "وقّع في السجل", search: "بحث", empty: "لا توجد رسائل بعد - كن الأول!",
            other: "English", count: "%d رسالة" },
}.freeze

helpers do
  def h(text) = Rack::Utils.escape_html(text.to_s)
  def lang = (params[:lang] == "ar" ? "ar" : "en")
  def t(key) = TEXTS[lang][key]
  def stars(n) = ("★" * n) + ("☆" * (5 - n))
end

get "/" do
  @entries = settings.store.search(params[:q])
  @errors = []
  @form = {}
  erb :index
end

post "/entries" do
  @form = { "name" => params[:name].to_s.strip, "message" => params[:message].to_s.strip,
            "rating" => params[:rating].to_i }
  @errors = EntryStore.validate(@form)
  if @errors.empty?
    settings.store.add(@form)
    redirect to("/?lang=#{lang}")
  else
    status 422
    @entries = settings.store.search(nil)
    erb :index
  end
end

post "/entries/:id/delete" do
  settings.store.delete(params[:id].to_i)
  redirect to("/?lang=#{lang}")
end

# JSON API: GET the list, POST {"name","message","rating"}
get "/api/entries" do
  content_type :json
  settings.store.search(params[:q]).to_json
end

post "/api/entries" do
  content_type :json
  data = JSON.parse(request.body.read) rescue {}
  form = { "name" => data["name"].to_s.strip, "message" => data["message"].to_s.strip, "rating" => data["rating"].to_i }
  errors = EntryStore.validate(form)
  halt 422, { errors: errors }.to_json unless errors.empty?
  status 201
  settings.store.add(form).to_json
end
