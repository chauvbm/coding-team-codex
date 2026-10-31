"""Small maintenance target with seeded defects; see TASKS.md for required behavior."""
import csv
import io
from copy import deepcopy
from heapq import heapify, heappop, heappush
from itertools import islice


def paginate(items, offset, limit):
    if offset < 0 or limit <= 0:
        raise ValueError("offset must be nonnegative and limit must be positive")
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
    prerequisites = {task: set(required) for task, required in dependencies.items()}
    nodes = set(prerequisites)
    for required in prerequisites.values():
        nodes.update(required)
    indegree = {task: len(prerequisites.get(task, ())) for task in nodes}
    dependants = {task: set() for task in nodes}
    for task, required in prerequisites.items():
        for prerequisite in required:
            dependants[prerequisite].add(task)
    ready = [task for task in nodes if indegree[task] == 0]
    heapify(ready)
    result = []
    while ready:
        task = heappop(ready)
        result.append(task)
        for dependant in dependants[task]:
            indegree[dependant] -= 1
            if indegree[dependant] == 0:
                heappush(ready, dependant)
    if len(result) != len(nodes):
        raise ValueError("dependencies contain a cycle")
    return result


def parse_csv_rows(text):
    records = csv.reader(io.StringIO(text, newline=""), strict=True)
    header = None
    result = []
    try:
        for row in records:
            if not row:
                continue
            if header is None:
                header = [name.strip() for name in row]
                if any(not name for name in header) or len(set(header)) != len(header):
                    raise ValueError("header names must be nonblank and unique")
            else:
                if len(row) != len(header):
                    raise ValueError("record length does not match header")
                result.append(dict(zip(header, row)))
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc
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
            raise ValueError("each transfer must have three values") from exc
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValueError("transfer amounts must be positive integers")
        try:
            accounts_exist = source in result and destination in result
        except TypeError as exc:
            raise ValueError("transfer accounts must exist") from exc
        if not accounts_exist:
            raise ValueError("transfer accounts must exist")
        if result[source] < amount:
            raise ValueError("insufficient funds")
        result[source] -= amount
        result[destination] += amount
    return result
