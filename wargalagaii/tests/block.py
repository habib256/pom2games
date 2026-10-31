"""The game state read back in one peek per memory area (2026-10-30: the
busiest state variables moved to zero page, the rest stayed in the BSS):
Block(L, {name: size}).peeks() for the steps, .read(r, k) -> {name: bytes}
from the k-th dumps."""


class Block:
    def __init__(self, L, sizes):
        self.L, self.sizes = L, dict(sizes)
        groups = {}
        for n, k in self.sizes.items():
            groups.setdefault(L[n] < 0x100, []).append((L[n], L[n] + k))
        self.ranges = [(min(a for a, _ in g), max(b for _, b in g) - min(a for a, _ in g))
                       for g in groups.values()]

    def peeks(self):
        return [f'peek:{a:04X}:{n}' for a, n in self.ranges]

    def read(self, r, k=0):
        out = {}
        for a, n in self.ranges:
            block = r.mem(a, n, k)
            for name, size in self.sizes.items():
                if a <= self.L[name] < a + n:
                    out[name] = block[self.L[name] - a:self.L[name] - a + size]
        return out
