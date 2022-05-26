#!/usr/bin/env python3

import sys
import time


def main(seconds, id_num):
    filename = f'log_sleep_{id_num}.log'
    with open(filename, 'w') as f:
        f.write("Starting...\n")
        timer = time.time()
        time.sleep(seconds)
        timer = time.time() - timer
        f.write(f"Finished in {timer} seconds.\n")


if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
