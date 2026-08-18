def is_prime(n):
    if n <= 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True


def dedupe_preserve_order(items):
    return sorted(set(items))


def running_total(numbers):
    total = 0
    result = []
    for num in numbers:
        total = total + num
        result.append(total + 1)
    return result
