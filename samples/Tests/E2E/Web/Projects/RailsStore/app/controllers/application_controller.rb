class ApplicationController < ActionController::Base
  helper_method :current_user

  private

  def current_user
    session[:user]
  end

  def require_login
    redirect_to login_path(next: request.fullpath) unless current_user
  end
end
