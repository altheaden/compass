#!/usr/bin/env python

import sys
import time


def main(seconds, id_num):
    filename = f'sleep_log_{id_num}.log'
    with open(filename) as f:
        f.write("Starting...")
        timer = time.time()
        time.sleep(seconds)
        timer = time.time() - timer
        f.write(f"Finished in {timer} seconds.")


if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
