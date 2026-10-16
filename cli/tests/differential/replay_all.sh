#!/bin/sh
# Replay pages $1..$2 with the prototype oracle (if not already done), then the
# Rust binary into $3 (default rust), then compare page records.
R=/home/tester/comic-reader/rust-candidate
PY=/home/tester/comic-reader/geometry-venv/bin/python
OUT=${3:-rust}
PAGES=$(seq -s, "$1" "$2")
cd $R
$PY -B $R/v63_replay_oracle.py $R/ledger-copy.jsonl $R/oracle "$PAGES" > $R/oracle.log 2>&1
mkdir -p $R/$OUT
: > $R/$OUT.log
for p in $(seq "$1" "$2"); do
  d=$R/$OUT/p$(printf %03d $p)
  [ -f $d/page-0001.json ] && continue
  ls $d/blocked-*.json >/dev/null 2>&1 && continue
  $R/comic-panel /home/tester/comic-reader/source.pdf $d.cbz --work-dir $d --ledger $R/ledger-copy.jsonl \
    --ledger-cap-usd 370 --render-cache /home/tester/comic-reader/replay-local/replay.json --pages $p \
    --reading-direction ltr --title 'V63 replay' --offline --page-cap-usd 0.50 > $d.log 2>&1
  echo "page $p: rust exit $?" >> $R/$OUT.log
done
$PY $R/compare_replay.py $R/oracle $R/$OUT "$PAGES" > $R/compare-$OUT.log 2>&1
echo done >> $R/compare-$OUT.log
