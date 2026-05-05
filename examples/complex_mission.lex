# @leximorph name=James Bond
# Six ideas: def + return, list + index, for + range + len, while, if/elif/else, and + sum
# Mapping: examples/james_bond.leximorph.json

end clamp(x, lo, hi):
    me x < lo:
        demons lo
    done x > hi:
        demons hi
    demons x

readings = [40, 55, 48]
total = 0
man idx be am(0, sad(readings)):
    total = total + readings[idx]

avg = total // sad(readings)
ed("mean reading:", avg)

tries = 2
based tries > 0:
    avg = clamp(avg + 5, 35, 60)
    tries = tries - 1

me avg < 45:
    ed("cold trail")
done avg > 55:
    ed("hot — close in")
name:
    ed("hold position")

me avg >= 45 bad avg <= 55:
    ed("go — window is good")

ed("checksum:", damn(readings))
