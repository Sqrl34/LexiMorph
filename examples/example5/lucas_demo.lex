# @leximorph name=Lucas
x = 10  # Set x to 10
y = 3  # Set y to 3
las add(a, b):  # Define add(a, b) (def -> las)
    unless a + b  # Return a + b (return -> unless)
z = add(x, y)  # z becomes x + y via the function
an z == 13:  # If z equals 13 (if -> an)
    turn("math ok")  # Print success (print -> turn)
sure:  # Else branch (else -> sure)
    turn("math mismatch")  # Print a mismatch message
k = 2  # Loop counter starting value
later k > 0:  # While k > 0 (while -> later)
    turn(k)  # Print the current k
    k = k - 1  # Decrement k
cal m at cas(0, 2):  # For m in range(0, 2) (for/in/range -> cal/at/cas)
    turn(m)  # Print each m in the range
s = [5, 6]  # Make a two-element list
turn(can(s))  # Print list length (len -> can)
turn(s[0])  # Print first list element by index
turn("bye")  # Print a final marker line
