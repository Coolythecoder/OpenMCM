# rc.8 native AVM1 text-format checks

The rc.8 standalone utility and the utility preserved inside the final staged
Journal both passed the expanded native TextField regression on 2026-09-12.
Each run captured 80 rows and asserted 72 rows plus pooled intermediate states,
checking 936 individual character formats. Eight sparse-format comparison rows
are captured diagnostics, not asserted production behavior.

These are native AVM1 TextField format-data checks in Ruffle 0.6.0 through
headless Microsoft Edge. The fixture does not replace TextField, HTML parsing,
or formatting methods. The host is compiled with MTASC `-keep` and the fixture
does not statically reference a production class, so the tested helper is the
one already embedded in the staged Journal.

## Coverage

- Header, label, and bold right-aligned value fonts; font aliases and sizes.
- Default white, explicit black, nested pink/green runs, and mixed font/size runs.
- Nested bold, italic, and underline overrides and inherited baseline styles.
- Named and decimal/hex numeric entities, including entities inside color runs.
- Native paragraph alignment and line breaks with exact carriage-return output.
- Empty, null, undefined, numeric, and boolean values.
- Persistent TextField identity across plain → HTML → plain assignment, with
  clean future defaults and per-character style verification at every stage.
- Embedded-font mode both enabled and disabled; future format unchanged.

## Newline regression found and corrected before packaging

A generated closing `</p>` added an unwanted final carriage return to multiline
inline HTML. Native unwrapped `One<br>Two` produces `One\rTwo`; the first rc.8
wrapper produced `One\rTwo\r`. Omitting only the generated closing paragraph tag
preserved explicit inherited alignment without adding that character. Final
production output matches unwrapped native output for line breaks, nested
paragraphs, differently aligned paragraphs, and text following a paragraph.

The three exploratory wrapper modes remain optional diagnostics. Each runs in
isolation with `--candidate=openParagraph`, `--candidate=innerOpenParagraph`, or
`--candidate=fontOnly`, and writes separately named result files. Candidate
results are not merged into the final production test counts.

## Reproduction and evidence

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp tests/avm1 -cp src/actionscript -cp .tools/mtasc-1.15/std8 -header 1280:720:30 -swf build/diagnostics/avm1-mouse/text-format-standalone-rc8.swf -version 8 -main tests/avm1/AVM1TextFormatStandalone.as
& .tools/mtasc-1.15/mtasc.exe -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/staging/Data/Interface/quest_journal.swf -out build/diagnostics/avm1-mouse/text-format-host-rc8.swf -keep -version 8 -main tests/avm1/AVM1TextFormatHost.as
$env:NODE_PATH='C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-text-format.cjs text-format-standalone-rc8.swf
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-text-format.cjs text-format-host-rc8.swf
```

Results and layered diagnostic screenshots are under
`build/diagnostics/avm1-mouse/text-format-standalone-rc8*` and
`build/diagnostics/avm1-mouse/text-format-host-rc8*`. Screenshots are not visual
parity evidence: the standalone browser does not supply Skyrim's font library.

The black/missing-glyph appearance reported in Skyrim was not reproduced in
Ruffle by the earlier rc.6/rc.7 helper either. Passing these tests does **not**
prove the screenshot's fault is fixed in game. Skyrim verification remains
necessary. This diagnostic work did not modify or launch the installed game.
