class SessionsController < ApplicationController
  def new
  end

  def create
    if params[:username] == "admin" &&
       ActiveSupport::SecurityUtils.secure_compare(params[:password].to_s, "secret")
      reset_session
      session[:user] = "admin"
      target = params[:next].to_s
      redirect_to(target.start_with?("/") ? target : products_path)
    else
      flash.now[:alert] = "Invalid user name or password"
      render :new, status: :unauthorized
    end
  end

  def destroy
    reset_session
    redirect_to root_path
  end
end
