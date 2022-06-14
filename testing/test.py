#!/usr/bin/env python3

def main():
    list1 = list()
    list2 = list()

    for i in range(10):
        list1.append(i)
        list2.append(i**2)

    # for i, j in list1, list2:
    #     print(f"{i}^2 = {j}")

    # for i, j in enumerate(list2):
    #     print(f"{i} squared is {j}")

    # [(x, y) for x in [1,2,3] for y in [3,1,4] if x != y]

    # [print(f"{i}^2 = {j}") for i in list1 for j in list2]

    # for (i, j) in zip(list1, list2):
    #     print(f"{i}^2 = {j}")

    dictionary = dict()
    dictionary['one'] = 1
    dictionary['two'] = 2
    dictionary['three'] = 3

    print(dictionary.items())
    print(dictionary.keys())
    print(dictionary.values())

    print(list(dictionary.keys()))
    print(list(dictionary.values()))
    print(list(dictionary.items()))


if __name__ == '__main__':
    main()
