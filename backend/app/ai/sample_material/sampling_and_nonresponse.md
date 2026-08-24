# Foundations of Survey Sampling and Non-Response Adjustment

**SYNTHETIC PROTOTYPE MATERIAL — NOT AN OFFICIAL PUBLICATION.**

This document was written specifically as sample input for the SAKSHYA
prototype's document-ingestion and question-generation pipeline. It is not
issued by, derived from, or affiliated with the National Statistical Office,
the Ministry of Statistics and Programme Implementation, or any government
body. Figures and thresholds below are illustrative teaching values chosen to
exercise the software, not official standards or real survey results.

---

## 1. Sampling Frames

A sampling frame is the list or procedure that identifies every unit in the
target population and provides a means of reaching them. The quality of a
frame determines the quality of everything built on it.

Three defects commonly affect frames. Undercoverage occurs when eligible units
are absent from the frame, so they have zero probability of selection and no
weighting adjustment can recover them. Overcoverage occurs when the frame
contains units outside the target population, such as demolished dwellings or
closed establishments. Duplication occurs when a single unit appears more than
once, which inflates its selection probability.

A frame should be assessed before selection, not after estimation has failed.
In this synthetic guidance we treat a frame with more than 5 percent
undercoverage of the target population as requiring documented remedial action
before it is used for a production survey.

## 2. Simple Random Sampling

Under simple random sampling without replacement, every possible sample of a
given size has an equal chance of being selected. If a population contains N
units and a sample of n units is drawn, each unit has selection probability
n divided by N.

The design weight attached to each selected unit is the reciprocal of its
selection probability, that is N divided by n. Design weights convert sample
totals into population estimates.

Simple random sampling is rarely used alone in large household surveys because
it does not guarantee adequate representation of small but important
subgroups, and because it ignores the cost advantages of clustering.

## 3. Stratified Sampling

Stratification divides the population into mutually exclusive and collectively
exhaustive groups called strata, and draws an independent sample within each
stratum. Strata are formed using variables known for every unit on the frame,
such as district, sector, or establishment size class.

Stratification reduces the variance of estimates when the strata are internally
homogeneous with respect to the survey variable. The gain comes from removing
between-stratum variation from the sampling error entirely.

Under proportional allocation the sample is distributed across strata in
proportion to stratum size, so the sampling fraction is constant and the design
is self-weighting. Under Neyman allocation the sample is distributed in
proportion to the product of stratum size and stratum standard deviation, which
minimises the variance of the overall estimate for a fixed total sample size.

Disproportionate allocation is used when a small stratum requires its own
reliable estimates. This oversampling must be corrected by weighting at the
estimation stage, or published totals will be biased toward the oversampled
stratum.

## 4. Sampling Weights

The final survey weight is normally constructed in three stages. The base
weight is the reciprocal of the selection probability. The non-response
adjusted weight multiplies the base weight by a factor that redistributes the
weight of non-responding units onto similar responding units. The calibrated
weight further adjusts the result so that survey estimates reproduce known
population totals from an external source such as a census projection.

Extreme weights inflate variance. A common practical safeguard in this
synthetic guidance is to trim weights exceeding four times the median weight
within a weighting class, and to document every trimming decision, because
trimming reduces variance at the cost of introducing a small bias.

## 5. Unit and Item Non-Response

Unit non-response occurs when a selected unit provides no usable data at all,
for example when a household is never contacted or refuses entirely. Item
non-response occurs when a responding unit fails to answer particular
questions, for example when a household completes the schedule but omits
income.

The two are treated differently. Unit non-response is normally handled by
weighting adjustment, because nothing is known about the missing unit beyond
its frame characteristics. Item non-response is normally handled by imputation,
because the responding unit supplies auxiliary information that makes a
prediction possible.

A low response rate is a warning sign, not a proof of bias. Non-response bias
depends on the product of the non-response rate and the difference between
respondents and non-respondents on the variable of interest. A survey with a
70 percent response rate where respondents and non-respondents are similar may
be less biased than a survey with a 90 percent response rate where they differ
sharply.

## 6. Weighting Class Adjustment

Weighting class adjustment groups sampled units into classes formed from
variables known for both respondents and non-respondents, such as stratum,
sector, or size class. Within each class the weights of responding units are
inflated by the reciprocal of the class response rate.

The method assumes that respondents and non-respondents within a class are
similar with respect to the survey variable. This is the missing-at-random
assumption conditional on the class variables, and it is an assumption, not a
finding. It should be stated explicitly in the methodology note.

Classes that are too small produce unstable adjustment factors. In this
synthetic guidance, weighting classes containing fewer than 20 responding units
should be collapsed with an adjacent class before adjustment factors are
computed.

## 7. Imputation

Imputation replaces a missing item value with a constructed value so that
analysis can proceed on a complete dataset. Mean imputation substitutes the
mean of responding units, which preserves the mean but understates variance and
distorts correlations. Hot-deck imputation copies a value from a similar
responding unit called the donor, which preserves the shape of the
distribution better than mean imputation. Regression imputation predicts the
missing value from auxiliary variables, and adding a random residual to the
prediction avoids the artificial reduction in variance that deterministic
regression imputation causes.

Every imputed value must carry an imputation flag in the dataset. Estimates
published from imputed data should report the imputation rate, because a
statistic derived largely from imputed values carries different reliability
from one derived from reported values.

## 8. Editing and Validation

Editing detects and resolves errors before estimation. Validity edits check
that a value lies within an admissible range or code list. Consistency edits
check that related values agree, for example that a reported age is compatible
with a reported marital status. Outlier detection identifies values that are
admissible but implausible relative to the distribution.

Selective editing concentrates effort on the errors that would most affect
published estimates, by scoring each suspicious record according to the likely
impact of its correction on the aggregate. This is more efficient than
attempting to resolve every flagged record, because most flagged records have
negligible influence on published totals.

Every automatic correction must be logged with the original value, the
corrected value, and the rule that fired, so that the editing process is
reproducible and auditable.

## 9. Statistical Disclosure Control

Disclosure control protects the confidentiality of respondents in published
outputs. Primary suppression removes cells that are unsafe because they
describe too few units or are dominated by a single unit. Secondary suppression
removes additional cells so that suppressed values cannot be recovered by
subtraction from published row and column totals.

A common threshold rule in this synthetic guidance is that a tabular cell
describing fewer than three units must be suppressed. A dominance rule
additionally suppresses a cell where a single unit contributes more than 60
percent of the cell total, because the dominant unit could otherwise deduce the
contribution of the others.

Perturbative methods, such as adding controlled noise or rounding to a fixed
base, are alternatives to suppression that preserve the shape of a table at the
cost of exactness. The method chosen must be documented and applied
consistently, because inconsistent application across releases can itself
create a disclosure risk.
