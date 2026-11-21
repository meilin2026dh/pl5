import math

def score_batch(history, candidates):
    recent = history[-120:]
    counts = [[1 for i in range(10)] for j in range(5)]
    for number in recent:
        for j in range(5):
            counts[j][int(number[j])] += 1
    out = []
    for candidate in candidates:
        score = 0.0
        for j in range(5):
            score += math.log(counts[j][int(candidate[j])] / (len(recent) + 10))
        out.append(score)
    return out
