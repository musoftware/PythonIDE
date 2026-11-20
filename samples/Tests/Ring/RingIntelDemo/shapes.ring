# Shapes library
func addNums a, b
    # Adds two numbers
    return a + b

class Point
    x = 0  y = 0
    func init nX, nY
        x = nX y = nY
        return self
    func moveBy dx, dy
        x += dx
        y += dy
    func show
        see "(" + x + "," + y + ")" + nl
