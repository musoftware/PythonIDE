class ProductsController < ApplicationController
  before_action :require_login, except: %i[ index show api ]
  before_action :set_product, only: %i[ show edit update destroy ]

  # GET /products
  def index
    @products = Product.order(:id)
  end

  # GET /products/1
  def show
  end

  # GET /products/new
  def new
    @product = Product.new
  end

  # GET /products/1/edit
  def edit
  end

  # POST /products
  def create
    @product = Product.new(product_params)

    if @product.save
      redirect_to @product, notice: "Product was successfully created."
    else
      render :new, status: :unprocessable_content
    end
  end

  # PATCH/PUT /products/1
  def update
    if @product.update(product_params)
      redirect_to @product, notice: "Product was successfully updated.", status: :see_other
    else
      render :edit, status: :unprocessable_content
    end
  end

  # DELETE /products/1
  def destroy
    @product.destroy!
    redirect_to products_path, notice: "Product was successfully destroyed.", status: :see_other
  end

  # GET /api/products
  def api
    render json: Product.order(:id).map { |p| { id: p.id, name: p.name, price: p.price.to_f } }
  end

  private
    # Use callbacks to share common setup or constraints between actions.
    def set_product
      @product = Product.find(params.expect(:id))
    end

    # Only allow a list of trusted parameters through.
    def product_params
      params.expect(product: [ :name, :price ])
    end
end
