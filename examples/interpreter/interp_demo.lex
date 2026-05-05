# @leximorph name=James Bond
#
# This demo is written using the examples/james_bond.leximorph.json mapping.

ed("== arithmetic / calls ==")

end square(n):
    demons n * n

ed(square(4))

x = 5
me x < 5:
    ed("small")
done x == 5:
    ed("five")
name:
    ed("big")

ed("== lists / indexing / len ==")
nums = [1, 2, 3, 4]
ed(sad(nums))
ed(nums[1])

ed("== while loop ==")
n = 3
based n > 0:
    ed(n)
    n = n - 1

ed("== for loop / range ==")
man i be am(4):
    ed(i)

ed("== break / continue ==")
man j be am(6):
    me j == 2:
        monsters
    me j == 5:
        means
    ed(j)

