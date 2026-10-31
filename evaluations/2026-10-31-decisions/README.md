# Decision evaluation record

This directory publishes coordinator-recorded results of decision simulations, including their requested model settings and limitations. It does not show a coding benchmark, cost saving, or native enforcement.

The baseline outputs contain 24 independent cases and four ordered turns at source commit `a45be4474b95b8f979285f13b9a5ec9a1859ddf2`. Transfer outputs contain six independent cases at source commit `45fe43435fd91da2bfdc140ded4ca6f3b9a25436`. Summary files pin provenance and disclose protocol corrections. Full model/tool transcripts and token/cost measurements are unavailable. Agent isolation was by instructions, not an enforced sandbox.

To reproduce scoring, use a separate checkout of the appropriate pinned commit, then pass the absolute path of the published response file to that checkout's checker:

```text
python tests/check_behavioral_results.py /absolute/path/to/behavioral_responses.json
python tests/check_behavioral_results.py --cases tests/sequential_cases.json /absolute/path/to/sequential_responses.json
python tests/check_behavioral_results.py --cases tests/reviewer_transfer_cases.json /absolute/path/to/reviewer_transfer_responses.json
```

Run the first two commands at the baseline commit and the third at the transfer commit. Later revisions may change the oracles. A current scoring pass is not a fresh model evaluation; inspect rationale and original fixture assumptions. Output files contain no account IDs, credentials, personal filesystem paths or live policy state.
