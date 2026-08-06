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

| Folder | Subject | Finding |
| --- | --- | --- |
| [json-conformance](json-conformance/) | `json` module, all ports | MicroPython accepts 47 of 188 documents that RFC 8259 declares invalid; `{"a": }` parses to `{}`, silently dropping the key |
