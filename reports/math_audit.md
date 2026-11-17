# Mathematical audit

Audit executed 4–5 November 2026. Scope: the synchronization-assurance definition, CoAP derivation and numeric values, simulation measurement definitions, and serialized cryptographic overhead. This report distinguishes proof, executed checks, and model limitations.

## 1. Synchronization-assurance bound

Let physical time be `t`, the generation instant `g`, and clock readings be `C_T(t)=t+e_T(t)` and `C_S(g)=g+e_S(g)`. An authentic generation timestamp is `C_S(g)`. Then

```
estimated_age = C_T(t) - C_S(g)
              = true_age + e_T(t) - e_S(g).
```

If `|e_T(t)-e_S(g)| <= epsilon(t)`, `true_age <= estimated_age + epsilon(t)`, so the manuscript's conservative freshness test is valid. The relevant errors are at two different instants. A same-instant source/twin offset bound alone needs an additional drift bound over the elapsed interval. A signature binds a timestamp to its source; accurate timestamp placement, clock integrity and trustworthy sampling are additional assumptions. The proposed definition is coherent under these explicit assumptions and need not be replaced.

A million randomly generated clock-error cases were evaluated as a sanity check (`results/clock_bound_check.json`): both clock errors lay within ±5 ms, so a 10 ms combined bound was used. No false-fresh acceptance occurred. This numerical test does not substitute for the algebraic proof. The manufacturing simulation uses the twin clock as its reference and source error ±5 ms, so its corresponding conservative margin is 5 ms.

**Necessary clarifications.** Identify the update currently supporting the held state. If a receiver replaces a newer observation with an older replay, held-observation age can increase discontinuously; the canonical freshest-sample AoI interpretation assumes no such regression. For fused state, test the age of each decision-relevant dependency; the newest of multiple inputs does not establish freshness of the oldest. Neither authenticated timestamps nor this time bound establish physical truth, as the spoofing experiment correctly illustrates.

## 2. CoAP derivation and independent calculations

[RFC 7252, §§4.2 and 4.8](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.2) specifies random initial timeout in [2,3] s at the default parameter values, four retransmissions, and doubling. The model's uniform distribution is an explicit additional assumption. Its five attempt times are `0,T0,3T0,7T0,15T0`. The default maximum transmit span is 45 s; this is a scheduling envelope, not a delivery deadline. Actual implementations can abandon or miss attempts, so the modeled uninterrupted schedule is not a universal behavior guarantee.

With independent loss probability `p`, first success at attempt `i` has mass `p^i(1-p)`. For a fixed one-way delay `delta` and generation coincident with first transmission, the sum in Eq. (2) follows by conditioning on that first success. For `i>0`, the timing factor is

```
clip(((D-delta)/(2^i-1)-2)/(3-2), 0, 1),
```

and for `i=0` it is `1{delta<=D}`. Total delivery probability is `1-p^5`. Lost acknowledgments can affect later duplicate transmissions and sender completion but cannot undo first reception; the model does not predict sender-confirmed exchange success. It assumes no spurious reset/cancellation or additional generation-to-transmission queue. Subsequent ingestion delay must be added when interpreting an application deadline.

Executed independent check: enumerate all 32 success/loss sequences, integrate the reception indicator over initial timeout using quadrature, and compare with the released formula at 168 combinations of loss, deadline and network delay. All absolute differences are below `1e-12` (`results/coap_independent_checks.csv`). At `p=.2, delta=.05 s`:

| Quantity | Verified probability |
| --- | ---: |
| Delivered over five attempts | 0.99968 = 99.968% |
| Delivered by 2 s | 0.8 |
| Delivered by 5 s | 0.96 |
| Delivered by 10 s | 0.992 |

The original 400,000-trial Monte Carlo check was executed for all 24 tested loss/deadline pairs. **A genuine rounding error was found:** the largest exact discrepancy is `0.0021100000000000008`. The prior four-decimal log printed `0.0021`, and the verifier tested that rounded value. The script now prints six decimals and checks `<=0.0022`; the manuscript should state within `2.2×10^-3`. No analytical probabilities or original numerical CSVs changed. This small observed Monte Carlo discrepancy is not a theorem or universal simulation error bound.

The probability is unconditional single-message reception before a deadline. It is neither a time-average AoI probability nor the fraction of decisions made on a fresh maintained state. Those require generation cadence, queueing, scheduling and receiver replacement policy.

A supplemental attempt-indexed two-state loss sensitivity holds stationary marginal loss at .2 and sets `P(loss_next|loss)=beta`. Delivery becomes `1-.2 beta^4`; at `beta=.8`, delivery is .91808 and timeliness at 2/5/10 s is .8/.84/.872. Four hundred thousand trials per beta were executed (`results/coap_correlated_loss_sensitivity.csv`). These are illustrative assumptions, not measured burst channels; attempts are indexed without physical-time correlation, and the added results should not be presented as field jamming measurements. The purpose is to show why the independent-loss qualification matters.

## 3. COSE and post-quantum sizes

The full original encoding/signing script ran successfully: plain payload 23 bytes; tagged Ed25519 and ES256 COSE_Sign1 100 bytes; tagged HMAC-256/64 COSE_Mac0 43 bytes. Overheads of 77 and 20 bytes are correct for the chosen integer widths, float32 value, protected algorithm identifier and one-byte unprotected key identifier. These are serialized message sizes, excluding network headers, public keys and certificates. They are not universal overhead constants or hardware timing measurements. Original host timing values were excluded from reproducibility equality checks.

The structure follows [RFC 9052, §§4.2 and 6.2](https://www.rfc-editor.org/rfc/rfc9052.html#section-4.2). [FIPS 204, Table 2](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf) gives ML-DSA signature lengths 2420/3309/4627 bytes for parameter sets 44/65/87, and [RFC 9964, §8.1.1](https://www.rfc-editor.org/rfc/rfc9964.html#section-8.1.1) supplies COSE identifiers -48/-49/-50. The audit encoded the same COSE envelope with fixed-length signature placeholders, yielding 2458/3347/4665 bytes. ML-DSA-44 overhead is 2435 bytes, `2435/77=31.62` times classical signature overhead. The minimum number of 127-byte containers is `ceil(2458/127)=20` before link/adaptation headers, so the stated lower bound is correct. No ML-DSA signing implementation, embedded-device timing or packet fragmentation experiment was executed.

## 4. Simulator definitions and corrections

The deterministic true threshold crossing is `300+(4.5-2.0)/.1=325 s`. The coded residual standard deviation is `sqrt(.1^2+(.05/.8)^2)` and the nominal threshold is five times this value divided by `sqrt(10)`. Its calibration assumes the modeled independent measurement-noise components; repeated/current-path samples and overlapping windows do not supply independent trials. This motivates the executed noise-calibration sensitivity rather than a universal Gaussian false-alarm claim.

The original C2/C3 policy tests estimated age against D without an epsilon guard. The original results are retained for exact reproduction; an optional `freshness_margin` now executes the conservative guard. A 5 ms guard leaves default attack conclusions intact, shifting stale-state alerts/actions 5 ms earlier. Thus original mean tables should be described as the estimated-age implementation, with the conservative variant separately identified.

I2 is undefined when no update is applied. I3 in the simulator includes rejected updates and arrivals outside the finite evaluation window; it is not the raw physical-link loss rate. I10 uses measured age and therefore is misleading when gateway timestamps are false. These interpretation boundaries must accompany the table. The combined no-attack I1 row previously displayed C0's .28 s for all configurations; source-based configurations have mean .29413 s, rounding to .29 s. No other displayed attack mean was contradicted by reproduction.
