"""Small maintenance utilities with isolated results and validated inputs."""
import csv
import io
from copy import deepcopy
import heapq
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
    prerequisites = {name: set(required) for name, required in dependencies.items()}
    all_nodes = set(prerequisites)
    for required in prerequisites.values():
        all_nodes.update(required)
    remaining = {name: len(prerequisites.get(name, ())) for name in all_nodes}
    dependants = {name: set() for name in all_nodes}
    for name, required in prerequisites.items():
        for prerequisite in required:
            dependants[prerequisite].add(name)
    ready = [name for name in all_nodes if remaining[name] == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        name = heapq.heappop(ready)
        ordered.append(name)
        for dependant in dependants[name]:
            remaining[dependant] -= 1
            if remaining[dependant] == 0:
                heapq.heappush(ready, dependant)
    if len(ordered) != len(all_nodes):
        raise ValueError("dependency cycle")
    return ordered


def parse_csv_rows(text):
    records = csv.reader(io.StringIO(text, newline=""))
    header = None
    result = []
    for record in records:
        if not record:
            continue
        if header is None:
            header = [name.strip() for name in record]
            if any(not name for name in header) or len(set(header)) != len(header):
                raise ValueError("header names must be nonblank and unique")
        else:
            if len(record) != len(header):
                raise ValueError("row must have exactly one cell per header")
            result.append(dict(zip(header, record)))
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
            raise ValueError("transfer must contain source, destination, amount") from exc
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("amount must be a positive integer")
        if source not in result or destination not in result:
            raise ValueError("unknown account")
        if result[source] < amount:
            raise ValueError("insufficient funds")
        result[source] -= amount
        result[destination] += amount
    return result
