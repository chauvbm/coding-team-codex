"""Small standard-library utilities with explicit validation and isolation."""
from copy import deepcopy
import csv
import heapq
import io
from itertools import islice


def paginate(items, offset, limit):
    if offset < 0 or limit <= 0:
        raise ValueError("offset must be nonnegative and limit positive")
    return list(islice(items, offset, offset + limit))


def deep_merge(base, overrides):
    result = deepcopy(base)
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(base[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def topological_order(dependencies):
    prerequisites = {node: set(values) for node, values in dependencies.items()}
    nodes = set(prerequisites)
    for values in prerequisites.values():
        nodes.update(values)
    remaining = {node: len(prerequisites.get(node, ())) for node in nodes}
    dependants = {node: set() for node in nodes}
    for node, values in prerequisites.items():
        for prerequisite in values:
            dependants[prerequisite].add(node)
    ready = [node for node in nodes if remaining[node] == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for dependant in dependants[node]:
            remaining[dependant] -= 1
            if remaining[dependant] == 0:
                heapq.heappush(ready, dependant)
    if len(result) != len(nodes):
        raise ValueError("dependencies contain a cycle")
    return result


def parse_csv_rows(text):
    records = csv.reader(io.StringIO(text, newline=""))
    header = None
    result = []
    for row in records:
        if not row:
            continue
        if header is None:
            header = [name.strip() for name in row]
            if any(not name for name in header) or len(set(header)) != len(header):
                raise ValueError("header names must be nonblank and unique")
        else:
            if len(row) != len(header):
                raise ValueError("record width does not match header")
            result.append(dict(zip(header, row)))
    return result


class ExpiringCache:
    def __init__(self):
        self.entries = {}

    def set(self, key, value, ttl, now):
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.entries[key] = (value, now + ttl)

    def get(self, key, now):
        if key not in self.entries:
            return None
        value, expires = self.entries[key]
        if now >= expires:
            del self.entries[key]
            return None
        return value


def apply_transfers(balances, transfers):
    result = balances.copy()
    for transfer in transfers:
        try:
            source, destination, amount = transfer
        except (TypeError, ValueError) as exc:
            raise ValueError("a transfer must contain source, destination and amount") from exc
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("transfer amounts must be positive integers")
        if source not in result or destination not in result:
            raise ValueError("both transfer accounts must exist")
        if result[source] < amount:
            raise ValueError("insufficient funds")
        result[source] -= amount
        result[destination] += amount
    return result
