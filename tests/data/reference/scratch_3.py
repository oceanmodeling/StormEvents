import math


def num_polynomials(dimensions: int, order: int) -> int:
    return (
        int(
            math.factorial(dimensions + order)
            / (math.factorial(dimensions) * math.factorial(order))
        )
        - 1
    )


if __name__ == '__main__':
    print(num_polynomials(4, 3))
    print(10 * num_polynomials(4, 3))

    print('done')
