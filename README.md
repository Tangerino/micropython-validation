MicroPython Validation

MicroPython Validation is an open-source repository dedicated to validating the MicroPython ecosystem through reproducible test cases, bug reports, regression tests, benchmarks, and practical workarounds.

Its primary goal is to improve the quality and reliability of MicroPython by providing a centralized knowledge base where developers can reproduce issues, verify fixes, compare behavior across versions and hardware platforms, and contribute new validation scenarios.

What you’ll find

* Reproducible bug reports
* Validation and integration tests
* Regression test cases
* Performance benchmarks
* Hardware compatibility results
* Workarounds and temporary fixes
* Comparison between MicroPython versions and ports

Principles

Every contribution should be:

* Reproducible — others should be able to reproduce the same behavior.
* Documented — include environment, firmware version, hardware, and reproduction steps.
* Objective — focus on observable behavior rather than assumptions.
* Reusable — help developers verify fixes and prevent regressions.

Scope

The repository covers all aspects of the MicroPython ecosystem, including (but not limited to):

* Core runtime
* uasyncio
* Networking
* Filesystems
* Drivers and peripherals
* Hardware ports
* ESP32, RP2040, STM32, Unix and other supported platforms
* Third-party libraries and integrations

Contributions are welcome from anyone interested in improving the stability, compatibility, and overall quality of MicroPython.

Validations

Every folder runs the same way — one command, no flags, nothing to clone by hand:

```sh
cd <folder>
./run.sh /path/to/micropython      # or just ./run.sh to use the one on your PATH
```

Whatever the validation needs — a test corpus, micropython-lib, an interpreter built with a
non-default option — `run.sh` fetches or builds it on first use and caches it. CPython runs
alongside as the reference, so the output is a comparison rather than a bare score.

| Folder | Subject | Finding |
| --- | --- | --- |
| [json-conformance](json-conformance/) | `json` module, all ports | MicroPython accepts 47 of 188 documents that RFC 8259 declares invalid; `{"a": }` parses to `{}`, silently dropping the key |
| [deflate-empty-input](deflate-empty-input/) | `deflate` module, all ports | Compressing empty input emits 0 bytes in RAW, ZLIB and GZIP; the result cannot be read back, not even by MicroPython's own decompressor |
| [unittest-behaviour](unittest-behaviour/) | `micropython-lib` / `unittest` | `setUp`/`tearDown` run outside the exception handler, so a skip or an error aborts the whole run; `main()` exits 0 on failure |
