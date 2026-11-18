# Face Recognition Evaluation Plan

## Current status

No accuracy, false-match rate, false-non-match rate, latency, demographic parity, or liveness performance is claimed by this project. The default similarity threshold is a development starting point only.

## Evaluation protocol

Before considering operational use:

1. Define the intended use, threat model, camera, capture distance, lighting, and environmental conditions.
2. Obtain an appropriately governed evaluation dataset with documented permissions and consent.
3. Split data by identity so that the same person cannot appear in both threshold-tuning and final test partitions.
4. Measure detection failure rate, false match rate (FMR), false non-match rate (FNMR), and end-to-end latency.
5. Evaluate across lighting, pose, occlusion, image quality, camera distance, and relevant population subgroups.
6. Test presentation attacks such as printed photographs, phone displays, and replayed video.
7. Choose the operating threshold using a validation set, then freeze it before final testing.
8. Report sample sizes, confidence intervals, model hashes, software versions, hardware, and known limitations.
9. Test duplicate and missed attendance events over realistic repeated visits.
10. Preserve a non-biometric workflow for anyone who cannot or does not wish to use face recognition.

## Metrics

- **Detection failure rate:** proportion of valid capture attempts where no usable face is detected.
- **FMR:** proportion of impostor comparisons incorrectly accepted.
- **FNMR:** proportion of genuine comparisons incorrectly rejected.
- **PAD error rates:** report attack presentation classification errors for each documented attack type.
- **Latency:** report capture-to-candidate time at median and tail percentiles on target hardware.
- **Operational event error:** duplicate, missed, incorrect-direction, and manually corrected event rates.

Similarity scores are not probabilities. A threshold such as `0.45` must not be interpreted as a 45% confidence level.
