"""Offline stand-in for an embedding model: a hashed bag of words. For tests only."""
import hashlib
import json
import re
import sys

vectors = []
for text in json.load(sys.stdin):
    vector = [0.0] * 64
    for word in re.findall(r'[a-z]+', text.lower()):
        vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % 64] += 1.0
    vectors.append(vector)
json.dump(vectors, sys.stdout)
