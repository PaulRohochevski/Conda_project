import numpy as np
import pandas as pd


def do():
    a: np.float = input('Insert start of the range (float, e.g. 0.1): ')
    a = np.float(a)
    b: np.float = input('Insert end of the range (float, e.g. 1.0): ')
    b = np.float(b)
    h: np.float = input('Insert range step (float, e.g. 0.2): ')
    h = np.float(h)
    n: int = input('Insert number of iterations (integer, e.g. 5): ')
    n = np.int(n)
    print('\n')

    arr = []

    for x in np.arange(a, b, h):
        yx = np.float64(y(x))
        sxn = np.float64(s(x, n))
        ys = np.float64(np.abs((y(x) - s(x, n))))
        arr.append([yx, sxn, ys])

    df = pd.DataFrame(arr, columns=['Y(x)', 'S(x, n)', '|Y(x) - S(x, n)|'], dtype=np.float64, index=np.arange(a, b, h))
    df.index.name = 'x'
    print(df)


def s(x: np.float, step: np.int) -> float:
    grand_total = 0
    for k in range(1, step + 1):
        grand_total += np.power(-1, (k + 1)) * np.power(x, (2 * k + 1)) / 4 * np.power(k, 2) - 1
    return grand_total


def y(x: np.float) -> float:
    return (1 + np.power(x, 2)) / 2 * np.arctan(x) - x / 2


if __name__ == '__main__':
    do()
