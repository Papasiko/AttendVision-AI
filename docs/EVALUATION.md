# Recognition evaluation plan

No accuracy, latency, or liveness performance is claimed by this scaffold.

Evaluate false match and false non-match rates, detection failures, PAD against a documented threat model, end-to-end latency on target hardware, duplicate/missed events, direction ambiguity, and performance across lighting, angle, and occlusion. Split datasets by person to avoid identity leakage. Record sample sizes, confidence intervals, threshold selection, model/version hashes, and limitations. Never tune thresholds on the final test set.
