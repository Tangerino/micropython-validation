# JSON parser conformance

Runs the industry-standard [JSONTestSuite](https://github.com/nst/JSONTestSuite) corpus
against MicroPython's `json` module, with CPython as the reference, and reports where the
two disagree.

**Finding: MicroPython accepts 47 documents that RFC 8259 declares invalid.** One of them
loses data silently.

## Result

| Parser | Must accept | Must reject | Crashes |
|---|---|---|---|
| CPython 3.13.3 | 95/95 | 185/188 | 0 |
| MicroPython `v1.29.0-preview.673` | 95/95 | **141/188** | 0 |

CPython's three misses are the well-known `NaN` / `Infinity` extensions, accepted by design
and switched off with `parse_constant`. MicroPython's 47 are not deliberate as far as the
documentation says.

The full per-case breakdown is in [RESULTS.md](RESULTS.md). Grouped:

| Group | Cases | Examples |
|---|---|---|
| Separators | 17 | `[1 true]`, `[1,,2]`, `[1:2]`, `{"a":1 "b":2}` |
| Numbers | 13 | `[-01]`, `[2.e3]`, `[1 000.0]`, `123.` |
| Strings and escapes | 12 | `["\a"]`, `["\uqqqq"]`, an unescaped newline |
| Structure | 5 | `{]`, `{"a":"b"}#` |

### The case that loses data

```python
>>> import json
>>> json.loads('{"a": }')
{}
```

The document is malformed, the parser reports success, and **the key disappears**. Nothing
raises, nothing warns. Downstream code applies its default as though the field had never
been written, so a truncated paste or a broken template becomes a silently missing value.

CPython raises `json.JSONDecodeError` for the same input.

This matters most for code that runs on both — a device and a Linux host sharing one
configuration file. The same file can load on both **with different contents**.

Neither parser crashed on any input, including the cases written to provoke it.
`n_structure_100000_opening_arrays.json` raises `MemoryError` on MicroPython, which is a
legitimate rejection rather than a fault.

## Environment

| | |
|---|---|
| MicroPython | `v1.29.0-preview.673.g06bcfd5b74`, commit `06bcfd5b7` |
| Port | unix, `build-standard`, default configuration |
| CPython | 3.13.3 |
| Host | macOS 15.5, arm64 |
| Corpus | JSONTestSuite, 318 cases (95 `y_`, 188 `n_`, 35 `i_`) |
| Date | 2026-08-06 |

## Reproducing

```sh
git clone --depth 1 https://github.com/nst/JSONTestSuite.git /tmp/jts
python3 report.py --suite /tmp/jts/test_parsing --interpreter micropython=/path/to/micropython
```

`report.py` is standalone — Python 3 and nothing else. It prints the Markdown you see in
[RESULTS.md](RESULTS.md).

For the pytest harness:

```sh
pip install pytest
pytest --suite /tmp/jts/test_parsing --interpreter micropython=/path/to/micropython
```

`--interpreter` is repeatable, so several builds or versions can be compared in one run.
CPython is always included as the reference: the useful question is not how many cases a
parser fails in the abstract, but how it differs from the implementation everyone writing
JSON already works against.

## Files

| File | Role |
|---|---|
| `probe.py` | walks the corpus and reports accept/reject per case. **Runs under CPython and MicroPython alike** — the comparison is only meaningful if both parsers get identical bytes from identical code |
| `conftest.py` | pytest options and fixtures; one process per interpreter, not per case |
| `test_conformance.py` | the assertions, split by what each case name promises |
| `report.py` | standalone Markdown report generator |
| `baseline.json` | the results above, recorded so CI fails only on *new* deviations |
| `RESULTS.md` | generated report for the environment listed above |

The corpus is not vendored here. It is MIT-licensed and lives upstream; clone it as shown.

## Using it in CI

A project that already deviates would start with dozens of red tests, which is how a useful
check gets switched off on its first day. Record the current behaviour once:

```sh
pytest --suite /tmp/jts/test_parsing --interpreter micropython=./micropython --write-baseline
```

From then on the suite is green and fails only when conformance gets **worse**. Deleting
entries from `baseline.json` as they are fixed turns it into a ratchet.

To see every deviation regardless of the baseline:

```sh
pytest --suite ... --interpreter ... --no-baseline
```

### GitHub Actions

Intended to be dropped into the MicroPython repository as-is:

```yaml
name: json-conformance

on: [push, pull_request]

jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build the unix port
        run: |
          make -C mpy-cross
          make -C ports/unix submodules
          make -C ports/unix

      - name: Fetch the corpus
        run: git clone --depth 1 https://github.com/nst/JSONTestSuite.git /tmp/jts

      - name: Run conformance
        run: |
          pip install pytest
          pytest json-conformance \
                 --suite /tmp/jts/test_parsing \
                 --interpreter micropython=ports/unix/build-standard/micropython

      - name: Report
        if: always()
        run: |
          python3 json-conformance/report.py \
                  --suite /tmp/jts/test_parsing \
                  --interpreter micropython=ports/unix/build-standard/micropython \
                  >> $GITHUB_STEP_SUMMARY
```

The last step writes the table into the run summary, so the state is visible without
opening logs.

## Design notes

**One process per interpreter, not per case.** 318 process spawns would turn a
30-millisecond run into a minute and tell us nothing extra.

**Results are flushed per case.** The corpus contains inputs meant to provoke a crash. If
one does, everything before it survives on disk and the first missing case names the file
that caused it — a crash is reported as a result rather than losing the run.

**Bytes are passed through undecoded.** Several cases carry deliberately invalid UTF-8;
decoding first would turn a parser question into a codec question.

**Every exception counts as a rejection**, `MemoryError` and `RecursionError` included. That
is the honest reading — the parser declined the input — and the corpus contains cases
designed to trigger exactly those.

## Is strict parsing affordable?

A relevant question for an implementation that trades correctness for size. While
investigating this, a strict structural validator written in plain Python scored **95/95 and
188/188** — full conformance, and stricter than CPython — in roughly 250 lines. It builds no
objects; it only walks the text and reports the offset of the first violation.

That does not settle what the right trade is for MicroPython's C parser, but it suggests
conformance is not inherently expensive.

## Related

MicroPython's parse errors also carry no position: `ValueError: syntax error in JSON`, with
no line or column. CPython reports both. For someone holding a device that will not boot,
that is the difference between a remote fix and a site visit.
