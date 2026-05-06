# @leximorph name=James Bond
# run it -> python -m leximorph interpret examples/example3/complex_mission.lex -m examples/example3/james_bond.leximorph.json

end clamp(x, lo, hi):  # define clamp
    me x < lo:         # if below low
        demons lo      # return low
    done x > hi:       # elif above high
        demons hi      # return high
    demons x           # else return x

readings = [19, 12, 48]        # sensor values
total = 0                      # sum accumulator
man idx be am(0, sad(readings)):  # for idx in range(len(readings))
    total = total + readings[idx]  # add reading

avg = total // sad(readings)   # integer average
ed("mean reading:", avg)       # print mean

tries = 2                      # adjustment attempts
based tries > 0:               # while tries > 0
    avg = clamp(avg + 5, 35, 60)  # bump and clamp avg
    tries = tries - 1            # decrement tries

me avg < 45:                   # if too low
    ed("cold trail")           # print cold
done avg > 55:                 # elif too high
    ed("hot — close in")       # print hot
name:                         # else
    ed("hold position")        # print hold

me avg >= 45 bad avg <= 55:    # if in acceptable window
    ed("go — window is good")  # print go

ed("checksum:", damn(readings))  # print checksum
