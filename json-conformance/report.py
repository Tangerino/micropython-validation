"""Produce a shareable Markdown report of JSON parser conformance.

Standalone: no pytest, no dependencies. Run it, paste the output into an issue.

    python3 report.py --suite /path/to/JSONTestSuite/test_parsing \\
                      --interpreter micropython=/path/to/micropython

The report leads with what the reader needs to decide something: how each parser
scores, then the deviations grouped by kind, then the handful of cases that make
the point on their own.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'probe.py')

#: Deviations grouped by what they mean, so a reader can see the shape of the
#: problem rather than a flat list of 47 file names.
GROUPS = (
    ('Separators', ('comma', 'colon', 'semicolon', 'separator')),
    ('Numbers', ('number', 'digit', 'multidigit')),
    ('Strings and escapes', ('string', 'escape', 'surrogate', 'unicode')),
    ('Structure', ('structure', 'object', 'array')),
    ('Literals', ('true', 'false', 'null', 'nan', 'infinity')),
)


def classify(case):
    lowered = case.lower()
    for label, keys in GROUPS:
        for key in keys:
            if key in lowered:
                return label
    return 'Other'


def run_probe(command, suite_dir, out_path):
    completed = subprocess.run(
        [command, PROBE, suite_dir, out_path], capture_output=True, text=True
    )
    results = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                line = line.rstrip('\n')
                if '\t' in line:
                    result, name = line.split('\t', 1)
                    results[name] = result
    if completed.returncode != 0:
        remaining = [
            n
            for n in sorted(os.listdir(suite_dir))
            if n.endswith('.json') and n not in results
        ]
        if remaining:
            results[remaining[0]] = 'crash'
    return results


def score(table):
    must_accept = [c for c in table if c.startswith('y_')]
    must_reject = [c for c in table if c.startswith('n_')]
    return {
        'accept_ok': sum(1 for c in must_accept if table[c] == 'y'),
        'accept_total': len(must_accept),
        'reject_ok': sum(1 for c in must_reject if table[c] == 'n'),
        'reject_total': len(must_reject),
        'crashes': sum(1 for c in table if table[c] == 'crash'),
        'wrongly_accepted': sorted(c for c in must_reject if table[c] == 'y'),
        'wrongly_rejected': sorted(c for c in must_accept if table[c] != 'y'),
    }


def excerpt(suite_dir, case, limit=48):
    """First line of a case file, for the illustrative table."""
    try:
        with open(os.path.join(suite_dir, case), 'rb') as f:
            raw = f.read(limit + 8)
    except OSError:
        return ''
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw)
    text = text.split('\n')[0]
    return text[:limit] + ('...' if len(text) > limit else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', required=True, help='JSONTestSuite/test_parsing')
    parser.add_argument(
        '--interpreter',
        action='append',
        default=[],
        help='name=command, repeatable',
    )
    parser.add_argument('--out', help='write the report here instead of stdout')
    args = parser.parse_args()

    interpreters = {'cpython': sys.executable}
    for entry in args.interpreter:
        name, _, command = entry.partition('=')
        interpreters[name] = command or name

    results = {}
    for name, command in interpreters.items():
        out_path = os.path.join(HERE, '.{}.tsv'.format(name))
        results[name] = run_probe(command, args.suite, out_path)
        try:
            os.remove(out_path)
        except OSError:
            pass

    scores = {name: score(table) for name, table in results.items()}
    lines = []
    add = lines.append

    add('# JSON parser conformance')
    add('')
    add(
        'Corpus: [JSONTestSuite](https://github.com/nst/JSONTestSuite) by Nicolas Seriot, '
        'from *Parsing JSON is a Minefield*. Case names carry the expectation: `y_` must '
        'be accepted, `n_` must be rejected, `i_` is left to the implementation by '
        'RFC 8259 and is not scored here.'
    )
    add('')
    add('## Summary')
    add('')
    add('| Parser | Must accept | Must reject | Crashes |')
    add('|---|---|---|---|')
    for name in sorted(scores):
        s = scores[name]
        add(
            '| `{}` | {}/{} | {}/{} | {} |'.format(
                name,
                s['accept_ok'],
                s['accept_total'],
                s['reject_ok'],
                s['reject_total'],
                s['crashes'],
            )
        )
    add('')

    reference = 'cpython'
    for name in sorted(scores):
        if name == reference:
            continue
        s = scores[name]
        wrongly_accepted = s['wrongly_accepted']
        if not wrongly_accepted:
            continue

        add('## `{}`: {} invalid documents accepted'.format(name, len(wrongly_accepted)))
        add('')
        add(
            'Each of these is malformed by RFC 8259. Accepting them means the document '
            'has no defined meaning, so two implementations can legitimately disagree '
            'about what it says — or, worse, one of them can silently read something '
            'different from the other.'
        )
        add('')

        by_group = {}
        for case in wrongly_accepted:
            by_group.setdefault(classify(case), []).append(case)

        add('| Group | Cases |')
        add('|---|---|')
        for group in sorted(by_group):
            add('| {} | {} |'.format(group, len(by_group[group])))
        add('')

        add('### The cases')
        add('')
        add('| Case | Input | `{}` | `{}` |'.format(reference, name))
        add('|---|---|---|---|')
        for case in wrongly_accepted:
            add(
                '| `{}` | `{}` | rejects | **accepts** |'.format(
                    case.replace('.json', ''), excerpt(args.suite, case)
                )
            )
        add('')

        if s['wrongly_rejected']:
            add('### Valid documents rejected')
            add('')
            add('| Case | Input |')
            add('|---|---|')
            for case in s['wrongly_rejected']:
                add(
                    '| `{}` | `{}` |'.format(
                        case.replace('.json', ''), excerpt(args.suite, case)
                    )
                )
            add('')

    reference_score = scores.get(reference)
    if reference_score and reference_score['wrongly_accepted']:
        add('## Reference deviations')
        add('')
        add(
            'For completeness: `{}` also accepts {} documents the corpus marks invalid. '
            'These are the well-known `NaN` / `Infinity` extensions, accepted by design '
            'and disabled with `parse_constant`.'.format(
                reference, len(reference_score['wrongly_accepted'])
            )
        )
        add('')
        for case in reference_score['wrongly_accepted']:
            add('- `{}`'.format(case.replace('.json', '')))
        add('')

    add('## Reproducing')
    add('')
    add('```sh')
    add('git clone --depth 1 https://github.com/nst/JSONTestSuite.git')
    add('python3 report.py --suite JSONTestSuite/test_parsing \\')
    add('                  --interpreter micropython=/path/to/micropython')
    add('```')
    add('')

    text = '\n'.join(lines)
    if args.out:
        with open(args.out, 'w') as f:
            f.write(text + '\n')
        print('report written to {}'.format(args.out))
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
