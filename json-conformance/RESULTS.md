# JSON parser conformance

Corpus: [JSONTestSuite](https://github.com/nst/JSONTestSuite) by Nicolas Seriot, from *Parsing JSON is a Minefield*. Case names carry the expectation: `y_` must be accepted, `n_` must be rejected, `i_` is left to the implementation by RFC 8259 and is not scored here.

## Summary

| Parser | Must accept | Must reject | Crashes |
|---|---|---|---|
| `cpython` | 95/95 | 185/188 | 0 |
| `micropython` | 95/95 | 141/188 | 0 |

## `micropython`: 47 invalid documents accepted

Each of these is malformed by RFC 8259. Accepting them means the document has no defined meaning, so two implementations can legitimately disagree about what it says — or, worse, one of them can silently read something different from the other.

| Group | Cases |
|---|---|
| Numbers | 13 |
| Separators | 17 |
| Strings and escapes | 12 |
| Structure | 5 |

### The cases

| Case | Input | `cpython` | `micropython` |
|---|---|---|---|
| `n_array_1_true_without_comma` | `[1 true]` | rejects | **accepts** |
| `n_array_colon_instead_of_comma` | `["": 1]` | rejects | **accepts** |
| `n_array_comma_and_number` | `[,1]` | rejects | **accepts** |
| `n_array_double_comma` | `[1,,2]` | rejects | **accepts** |
| `n_array_double_extra_comma` | `["x",,]` | rejects | **accepts** |
| `n_array_extra_comma` | `["",]` | rejects | **accepts** |
| `n_array_inner_array_no_comma` | `[3[4]]` | rejects | **accepts** |
| `n_array_items_separated_by_semicolon` | `[1:2]` | rejects | **accepts** |
| `n_array_just_comma` | `[,]` | rejects | **accepts** |
| `n_array_missing_value` | `[   , ""]` | rejects | **accepts** |
| `n_array_number_and_comma` | `[1,]` | rejects | **accepts** |
| `n_array_number_and_several_commas` | `[1,,]` | rejects | **accepts** |
| `n_multidigit_number_then_00` | `123.` | rejects | **accepts** |
| `n_number_-01` | `[-01]` | rejects | **accepts** |
| `n_number_-2.` | `[-2.]` | rejects | **accepts** |
| `n_number_0.e1` | `[0.e1]` | rejects | **accepts** |
| `n_number_1_000` | `[1 000.0]` | rejects | **accepts** |
| `n_number_2.e+3` | `[2.e+3]` | rejects | **accepts** |
| `n_number_2.e-3` | `[2.e-3]` | rejects | **accepts** |
| `n_number_2.e3` | `[2.e3]` | rejects | **accepts** |
| `n_number_neg_int_starting_with_zero` | `[-012]` | rejects | **accepts** |
| `n_number_neg_real_without_int_part` | `[-.123]` | rejects | **accepts** |
| `n_number_real_without_fractional_part` | `[1.]` | rejects | **accepts** |
| `n_number_with_leading_zero` | `[012]` | rejects | **accepts** |
| `n_object_comma_instead_of_colon` | `{"x", null}` | rejects | **accepts** |
| `n_object_double_colon` | `{"x"::"b"}` | rejects | **accepts** |
| `n_object_garbage_at_end` | `{"a":"a" 123}` | rejects | **accepts** |
| `n_object_missing_key` | `{:"b"}` | rejects | **accepts** |
| `n_object_missing_semicolon` | `{"a" "b"}` | rejects | **accepts** |
| `n_object_non_string_key` | `{1:1}` | rejects | **accepts** |
| `n_object_non_string_key_but_huge_number_instead` | `{9999E9999:1}` | rejects | **accepts** |
| `n_object_repeated_null_null` | `{null:null,null:null}` | rejects | **accepts** |
| `n_object_several_trailing_commas` | `{"id":0,,,,,}` | rejects | **accepts** |
| `n_object_trailing_comma` | `{"id":0,}` | rejects | **accepts** |
| `n_object_two_commas_in_a_row` | `{"a":"b",,"c":"d"}` | rejects | **accepts** |
| `n_object_with_single_string` | `{ "foo" : "bar", "a" }` | rejects | **accepts** |
| `n_string_backslash_00` | `["\."]` | rejects | **accepts** |
| `n_string_escape_x` | `["\x00"]` | rejects | **accepts** |
| `n_string_escaped_ctrl_char_tab` | `["\."]` | rejects | **accepts** |
| `n_string_escaped_emoji` | `["\...."]` | rejects | **accepts** |
| `n_string_incomplete_surrogate_escape_invalid` | `["\uD800\uD800\x"]` | rejects | **accepts** |
| `n_string_invalid_backslash_esc` | `["\a"]` | rejects | **accepts** |
| `n_string_invalid_unicode_escape` | `["\uqqqq"]` | rejects | **accepts** |
| `n_string_unescaped_newline` | `["new.line"]` | rejects | **accepts** |
| `n_string_unescaped_tab` | `["."]` | rejects | **accepts** |
| `n_string_unicode_CapitalU` | `"\UA66D"` | rejects | **accepts** |
| `n_structure_open_object_close_array` | `{]` | rejects | **accepts** |

## Reference deviations

For completeness: `cpython` also accepts 3 documents the corpus marks invalid. These are the well-known `NaN` / `Infinity` extensions, accepted by design and disabled with `parse_constant`.

- `n_number_NaN`
- `n_number_infinity`
- `n_number_minus_infinity`

## Reproducing

```sh
git clone --depth 1 https://github.com/nst/JSONTestSuite.git
python3 report.py --suite JSONTestSuite/test_parsing \
                  --interpreter micropython=/path/to/micropython
```

