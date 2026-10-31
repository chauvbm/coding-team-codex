"""Small maintenance target with seeded defects; see TASKS.md for required behavior."""
import csv
import io


def paginate(items, offset, limit):
    return list(items)[offset:limit]


def deep_merge(base, overrides):
    result = base.copy()
    result.update(overrides)
    return result


def topological_order(dependencies):
    return sorted(dependencies)


def parse_csv_rows(text):
    return list(csv.DictReader(io.StringIO(text)))


class ExpiringCache:
    entries = {}

    def set(self, key, value, ttl, now):
        self.entries[key] = (value, now + ttl)

    def get(self, key, now):
        value, expires = self.entries.get(key, (None, now))
        return value if now <= expires else None


def apply_transfers(balances, transfers):
    for source, destination, amount in transfers:
        balances[source] -= amount
        balances[destination] += amount
    return balances
