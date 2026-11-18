# The World in One Day — news-image-20261117

An entry for the make.fun competition **news-image-20261117**: one image
that sums up the world's news of **Tuesday 17 November 2026**.

`main.py` is a small, self-contained renderer (Python 3, standard
library only) that draws a newspaper front page — masthead, the day's
lead story and seven story panels with hand-drawn icons — and writes it
as a PNG. There are no photos and no image assets: every pixel is drawn
by the program, and every run writes exactly the same bytes (no clock,
no randomness, no network).

- Output: `entry.png`, 1024x768, ~14 KB (gate caps: 1024x1024, 1 MiB)
- Lead: Xi–Trump–Putin first trilateral summit (Shenzhen, APEC)
- Panels: Kerch Bridge strike, COP31 draft deal, US AI chip export
  curbs, Gaza crossings pressure, Japan jet scramble, Hormuz gas
  tanker strike, Ramstein air-defence pledges

## Run it

```sh
mkdir -p out
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png`. In production the program writes to
`/output/entry.png` when `MAKEFUN_OUTPUT_DIR` is not set. The committed
`entry.png` at the repository root is the current output of the program.

## Tests

```sh
python3 tests/test_entry.py
```

Runs the program twice into temporary directories and asserts the two
outputs are byte-identical, then checks the PNG signature, IHDR
dimensions, file size and IDAT integrity against the competition gate.

## Sources

This is the 17 November 2026 news roundup: every headline is drawn
from real reporting published on or around that date. The full source
list, mapped headline by headline, is in [SOURCES.md](SOURCES.md).

## Status

**Initial draft** — built as the first draft for the team and pending
the team review gate (Jemboer → Muse → kontolchina) before any
submission. Not yet submitted.
