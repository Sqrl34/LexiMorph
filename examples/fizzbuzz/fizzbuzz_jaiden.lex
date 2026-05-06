# @leximorph name=jaiden
# run string -> python -m leximorph interpret examples/fizzbuzz/fizzbuzz_jaiden.lex -m examples/fizzbuzz/jaiden.leximorph.json

# FizzBuzz 1..100 (jaiden mapping)
die i id din(1, 101):
    an i % 15 == 0:
        dia("FizzBuzz")
    jane i % 3 == 0:
        dia("Fizz")
    jane i % 5 == 0:
        dia("Buzz")
    idea:
        dia(i)