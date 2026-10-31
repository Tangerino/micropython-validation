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
| [unix-macos-thread-gc-semaphore](unix-macos-thread-gc-semaphore/) | unix port, macOS | The GC semaphore is named after `pthread_self()` of the main thread, identical in every process; with two or more interpreters running, all but one collect without waiting for their threads to scan their stacks and crash (16 of 24 concurrent processes). Linux unaffected |
| [esp32-rom-memoryview-slice-store](esp32-rom-memoryview-slice-store/) | esp32 port, v1.29.0 | `machine.mem_backup()[0:1] = b"\x11"` panics the board: a slice store rewrites `len`/`free` of a memoryview that lives in flash. Fixed on master 2026-08-27, not yet released |
| [esp32-upstream-suite-v1.29](esp32-upstream-suite-v1.29/) | esp32 port, v1.29.0, hardware | The whole upstream suite on a production ESP32, bytecode and native Xtensa, with a unix v1.29.0 control: 960/964 and 706/709 pass, three failures are version skew, one is the crash above |
