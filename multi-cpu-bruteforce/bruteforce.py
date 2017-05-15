import itertools
import string
import random
import sys
import multiprocessing

def bruteforce(charset, maxlen, startposition):
    return (''.join(candidate)
            for candidate in itertools.chain.from_iterable(itertools.product(charset, repeat=i)
            for i in range(startposition, maxlen + 1)))

alnum_charset = string.ascii_lowercase + string.ascii_uppercase + "0123456789"
alnumsymbol_charset = alnum_charset + "!@#$%^&*()-_+=[]{}|\/.,;:\'\"`~"

def gen_rand_password(charset, pass_len):
    return ''.join(charset[random.randrange(len(charset))] for i in xrange(pass_len))

def attempt_bruteforce(password, maxlen, startposition):
    for attempt in bruteforce(alnumsymbol_charset, maxlen, startposition):
        if attempt == password:
            print password
            sys.exit()
        else:
            continue

def main():
    password = gen_rand_password(alnumsymbol_charset, 2)
    jobs = []
    procs = 8
    for i in xrange(0, procs):
        process = multiprocessing.Process(target=attempt_bruteforce, args=(alnumsymbol_charset, 4, i))
        process.daemon = True
        jobs.append(process)

    for j in jobs:
        j.start()

    for j in jobs:
        j.join()

if __name__ == '__main__':
    main()
