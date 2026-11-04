import math

def score_batch(history, candidates):
    last = history[-120:]
    c = [{str(i): 1 for i in range(10)} for _ in range(5)]
    for row in last:
        for j, digit in enumerate(row):
            c[j][digit] = c[j][digit] + 1
    results = []
    length = len(last) + 10
    for number in candidates:
        values = [math.log(c[j][number[j]] / length) for j in range(5)]
        results.append(sum(values))
    return results
