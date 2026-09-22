#!/usr/bin/env bash
# Fails if any document still describes a pipeline that no longer exists.
#
# Two passes. The negative one catches text that should have been deleted; the positive one
# catches a file nobody opened, which a negative grep can never find.
#
# Not a test framework -- a grep with an allowlist, readable in one sitting.
# Runs from Git Bash on Windows. Usage: tools/check-docs.sh

set -u
cd "$(dirname "$0")/.." || exit 2

fails=0
note() { printf '  %s\n' "$*"; }

# specs/ and eda/ are a dated record: they say what was true when they were written.
# Landing and Bronze keep 121, which counts tickers requested from Yahoo, not dimension rows.
EXCLUDES=(
  --exclude-dir=.git --exclude-dir=.agents --exclude-dir=.claude --exclude-dir=node_modules
  --exclude-dir=specs --exclude-dir=eda --exclude-dir=tools
  --exclude-dir="Claude outputs"
)
SKIP_PATH='^./etl/00_landing/|^./etl/01_bronze/|^./ddl/00_landing/|^./ddl/01_bronze/|course-brief'

# ---------------------------------------------------------------- negative pass
# Each entry is  pattern<TAB>why it must not appear.
#
# Phrases and identifiers are searched everywhere: a stale one in a notebook comment matters
# as much as in the README.
PHRASES=(
  'fact_monthly_performance	the monthly fact was retired in step 13'
  'true star	the bridge means the model is no longer a pure star'
  'atomic fact	there is only one fact now'
  'aggregate fact	there is only one fact now'
  'base-fact	there is only one fact now'
  'two facts	there is only one fact now'
  '44 tasks	the task count is 25 DDL and 17 ETL'
  '23 DDL	the DDL task count is 25 since step 13'
  '15 ETL	the ETL task count is 17 since step 13'
  'three SCD2 drivers	status stopped being a driver at step 11'
  '05_orchestration/workflow	the step 7 restructure moved it to orchestration/'
  'reported twice	survivorship reporting was removed at step 11'
  'survivors only	survivorship reporting was removed at step 11'
  'including and excluding	survivorship reporting was removed at step 11'
)

# Bare numbers are searched in prose only. In a notebook they collide with the hex nuids
# Databricks puts on every cell, and in a .csv or a lock file they are just data.
NUMBERS=(
  '15,604	pre-listed-only monthly row count; now 15,333'
  '15604	pre-listed-only monthly row count; now 15,333'
  '445	pre-listed-only horizon row count; now 440'
  '121	pre-listed-only dim_ticker row count; now 102'
)

scan() { # scan <pattern> [extra grep args...]
  local pattern="$1"; shift
  grep -rniF "$pattern" . "${EXCLUDES[@]}" --binary-files=without-match -l "$@" 2>/dev/null \
    | grep -Ev "$SKIP_PATH" || true
}

scan_number() { # scan_number <digits> [extra grep args...]
  # Bounded so 121 does not match inside 35,121, inside a CSS hex like #121B20, or inside a
  # word; and 445 does not match inside 1,445.
  local n="$1"; shift
  grep -rniE "(^|[^0-9,.#A-Za-z])${n}($|[^0-9,.A-Za-z])" . "${EXCLUDES[@]}" --binary-files=without-match -l "$@" 2>/dev/null \
    | grep -Ev "$SKIP_PATH" || true
}

report() { # report <pattern> <why> <hits>
  [ -z "$3" ] && return 0
  fails=$((fails + 1))
  printf '  FAIL  "%s" -- %s\n' "$1" "$2"
  while IFS= read -r f; do [ -n "$f" ] && note "        $f"; done <<< "$3"
}

echo "negative pass -- text that should be gone"
before_negative=$fails
for entry in "${PHRASES[@]}"; do
  report "${entry%%	*}" "${entry##*	}" "$(scan "${entry%%	*}")"
done
for entry in "${NUMBERS[@]}"; do
  report "${entry%%	*}" "${entry##*	}" \
    "$(scan_number "${entry%%	*}" --include='*.md' --include='*.html')"
done
[ "$fails" -eq "$before_negative" ] && echo "  clean"

# ---------------------------------------------------------------- positive pass
# A file that describes the model must describe the model we actually have.
echo
echo "positive pass -- the new model is actually described"
MODEL_DOCS=(
  README.md
  docs/PRD.md
  CLAUDE.md
  personaldocs/PRESENTATION.md
  personaldocs/DEFENSA-ES.md
  docs/star-schema.html
  personaldocs/star-schema-es.html
)
REQUIRED=(bridge_ticker_manager dim_manager dim_management_group)

for doc in "${MODEL_DOCS[@]}"; do
  if [ ! -f "$doc" ]; then
    note "skip  $doc (not present)"
    continue
  fi
  missing=""
  for term in "${REQUIRED[@]}"; do
    grep -qF "$term" "$doc" || missing="$missing $term"
  done
  if [ -n "$missing" ]; then
    fails=$((fails + 1))
    printf '  FAIL  %s is missing:%s\n' "$doc" "$missing"
  fi
done
echo "  checked ${#MODEL_DOCS[@]} documents"

# ------------------------------------------------------------- standing check
# The name is never written down here -- that would put it in the repo, which is the
# thing being prevented. Set EMPLOYER_NAME in the environment to run this check.
echo
echo "standing check -- employer name"
if [ -n "${EMPLOYER_NAME:-}" ]; then
  hits=$(grep -rniF "$EMPLOYER_NAME" . "${EXCLUDES[@]}" -l 2>/dev/null || true)
  if [ -n "$hits" ]; then
    fails=$((fails + 1))
    printf '  FAIL  employer name appears in:\n'
    while IFS= read -r f; do [ -n "$f" ] && note "        $f"; done <<< "$hits"
  else
    echo "  clean"
  fi
else
  echo "  skipped -- set EMPLOYER_NAME to enable"
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "PASS"
  exit 0
fi
echo "FAIL -- $fails check(s) failed"
exit 1
