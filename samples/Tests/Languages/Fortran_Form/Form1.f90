! Event handlers for Form1 (debugger test)
module form1_code
  use radgui
  implicit none
contains

  subroutine Form1_Load()
  end subroutine Form1_Load

  subroutine cmdAdd_Click()
    integer :: a, b, total
    a = 2
    b = 3
    total = a + b
    call rad_set("lblOut", "Caption", "done")
  end subroutine cmdAdd_Click

end module form1_code
