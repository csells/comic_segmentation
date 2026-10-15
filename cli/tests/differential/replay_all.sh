#!/bin/sh
# Replay pages $1..$2 with the prototype oracle, then the Rust binary, then compare.
R=/home/tester/comic-reader/rust-candidate
PY=/home/tester/comic-reader/geometry-venv/bin/python
PAGES=$(seq -s, "$1" "$2")
cd $R
$PY -B $R/v63_replay_oracle.py $R/ledger-copy.jsonl $R/oracle "$PAGES" > $R/oracle.log 2>&1
for p in $(seq "$1" "$2"); do
  d=$R/rust/p$(printf %03d $p)
  [ -f $d/page-0001.json ] && continue
  ls $d/blocked-*.json >/dev/null 2>&1 && continue
  $R/comic-panel /home/tester/comic-reader/source.pdf $d --ledger $R/ledger-copy.jsonl --budget-cap-usd 370 \
    --render-cache /home/tester/comic-reader/replay-local/replay.json --pages $p --reading-direction ltr \
    --title 'V63 replay' --offline --page-cap-usd 0.50 --auto-transient-recovery > $d.log 2>&1
  echo "page $p: rust exit $?" >> $R/rust.log
done
$PY $R/compare_replay.py $R/oracle $R/rust "$PAGES" > $R/compare.log 2>&1
echo done >> $R/compare.log
