"""Run the JSONTestSuite corpus through whichever interpreter executes this file.

The same script runs under CPython and under MicroPython, on purpose: the whole
value of the comparison rests on both parsers being handed identical bytes by
identical code.

    python3      probe.py <suite_dir> [output.tsv]
    micropython  probe.py <suite_dir> [output.tsv]

Output is one tab-separated line per case::

    y	y_string_space.json
    n	n_object_trailing_comma.json
    crash	n_structure_100000_opening_arrays.json

``y`` means the parser accepted the input, ``n`` that it rejected it, and
``crash`` that the process died — which the corpus is designed to provoke and
which is itself a result worth reporting.

Results are written and flushed one at a time, so a hard crash still leaves
everything up to the offending case on disk. The file that killed the process is
then the first one missing from the output.

No argparse and no f-strings: this has to run on a bare MicroPython build.
"""

import os
import sys

try:
    import ujson as json
except ImportError:
    import json

ACCEPTED = 'y'
REJECTED = 'n'
CRASHED = 'crash'


def cases(suite_dir):
    """Every test case in the corpus, sorted so runs are comparable."""
    names = [n for n in os.listdir(suite_dir) if n.endswith('.json')]
    names.sort()
    return names


def try_parse(path):
    """Return ``'y'`` if the parser accepted the file, ``'n'`` if it rejected it.

    Bytes are passed straight through rather than decoded first: several cases
    carry deliberately invalid UTF-8, and decoding here would turn a parser
    question into a codec question.

    Every exception counts as a rejection, including MemoryError and
    RecursionError. That is the honest reading — the parser declined the input —
    and the corpus contains cases designed to trigger exactly those.
    """
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except OSError:
        return REJECTED

    try:
        json.loads(raw)
        return ACCEPTED
    except Exception:
        return REJECTED


def main(argv):
    if len(argv) < 2:
        print('usage: probe.py <suite_dir> [output.tsv]')
        return 2

    suite_dir = argv[1]
    out_path = argv[2] if len(argv) > 2 else None
    out = open(out_path, 'w') if out_path else None

    done = 0
    for name in cases(suite_dir):
        result = try_parse(suite_dir + '/' + name)
        line = '{}\t{}\n'.format(result, name)
        if out is not None:
            out.write(line)
            # Flushed per case so a crash leaves a usable partial result. The
            # first missing case names the file that killed the process.
            try:
                out.flush()
            except (AttributeError, OSError):
                pass
        else:
            sys.stdout.write(line)
        done += 1

    if out is not None:
        out.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
