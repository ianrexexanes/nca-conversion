# The /cro compare procedure

This is the procedure `/cro compare` follows. It writes the plugin's folder as `${CLAUDE_PLUGIN_ROOT}`. The shell does not set it, so put the full path the `cro` skill gave you in its place in every command you run and every file you read. Any argument that can hold a space, such as a folder name, goes in quotation marks. The output is a before and after of one page, internal first and then a client version, and it says where no before and after can be made.

Two audits are comparable only within one mode, one method and one set of anchors. The script checks that for you and prints what it could not compare. It never subtracts across that line.

1. Find the two audit data folders of the same page. They sit in `<project folder>/_audit-data/`, named `<page-slug>-<YYYY-MM-DD>`. The older one is the before folder and the later one is the after folder. Check that they are one page: the `page` value in each `score.json` and the `url` in each facts file must match. When they do not, say so and stop, because a comparison of two pages shows nothing.
2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/compare.py <before folder> <after folder>`. Add `--json` for the same lines as data. On exit code 2 the stderr lines each name the side and the file to fix. Fix the file's format or find the right folder, and rerun. A sheet's scores are never edited to make a comparison run.
3. Read the lines by what each case means.
   - `New baseline`: the mode or the page role changed, so the after audit is the new baseline. No before and after is written.
   - The version note: a sheet without `plugin_version` reads as the oldest anchors, and the line says which sheet it is.
   - `Anchors changed in 0.3.0`: the two scores were set with different anchors. Read them side by side, never as a change, and name no factor as better or worse.
   - The factor lines: a factor scored on both sides shows its change, and a factor scored on one side is not compared. There is no total change line, because two totals over different sets of factors do not subtract.
   - The speed lines: shown only when both sides used one source, such as PageSpeed Insights on both. Two sources are not compared.
   - The search lines: shown only for one confirmed keyword. A changed keyword is a new test.
   - The facts lines: the title, the meta description, the H1, the H2 list, the button labels and the form count, each shown when it changed. A footer heading counts in the H2 list on facts from before 0.3.0, which cannot say which headings sit in a footer.
   - `The result cannot be put down to either change.`: the H1 and a button label changed together.
4. Write `compare.md` in the after audit's data folder. Put the script's lines in word for word, then what they mean for this page, then which leaks of the before audit are fixed and which are open. Check each leak against the after audit's own evidence, and mark one as fixed only when the after audit shows it.
5. Write the client version, `<project folder>/Before and After — <Page> — <YYYY-MM-DD> — client.md`, dated the after audit's day. Follow `client-version.md`: the client version lists the fixed leaks and the open leaks and gives no score and no factor table. Then run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py <client file>` and fix every FAIL.
6. State the test rule for the next round: a live test changes one thing at a time. When the H1 and a button label changed together, the result cannot be put down to either change, so the next test changes only one of them and keeps the other as it is. A new baseline starts a new run of tests, and the old audit stays as history.
