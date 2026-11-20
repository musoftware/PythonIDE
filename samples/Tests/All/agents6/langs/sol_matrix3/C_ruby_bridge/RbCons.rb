require_relative "golib_ref"
require_relative "lualib_ref"
require_relative "rblib_ref"
require_relative "pylib_ref"
require_relative "cslib_ref"
module RbCons
  module_function
  def T_GoLib
    GoLib.Add(2, 3)
  end
  def T_LuaLib
    LuaLib.Add(2, 3)
  end
  def T_RbLib
    RbLib.Add(2, 3)
  end
  def T_PyLib
    PyLib.Add(2, 3)
  end
  def T_CsLib
    CsLib.Add(2, 3)
  end
end
