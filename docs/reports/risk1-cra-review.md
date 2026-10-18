# Risk 1 review: does our reading match the CRA?

Phase 2, Q9.1, risk 1: our interpretation of awareness time, fix availability, the 14-day
final report, and the final report's contents might not match the CRA. The planned
investigation was for Team 17, during Phase 3, to review the CRA provisions against Models
C and D. This is that review.

- **Done:** 2026-10-18, by Quincy's agent (Claude Code), reviewed with Quincy.
- **Source:** Regulation (EU) 2024/2847, the EUR-Lex print version saved 2026-09-09
  ([`source/regulation-2024-2847-cra.pdf`](source/regulation-2024-2847-cra.pdf)). Every
  quote below was checked word for word against that file.
- **Compared against:** [`docs/spec.md`](../spec.md) (REQ-02 to REQ-08, Models C and D).

## Summary

The deadlines and required report contents match Article 14(2). One gap makes a deadline
too late (Finding 1), and one rule is stricter than the law in a way that can block a
timely record (Finding 2). Both are shared-spec questions for Team 21, and are listed as
open questions Q8 and Q9 in [`docs/plan.md`](../plan.md). Neither changes the shared scope
yet.

## What matches

| Provision | Text | Our spec |
|---|---|---|
| Art. 14(2)(a) | an early warning "without undue delay and in any event within 24 hours of the manufacturer becoming aware of it" | REQ-04: awareness + 24 h. Our due time is the outer limit; "without undue delay" means earlier can be expected. |
| Art. 14(2)(b) | a vulnerability notification "without undue delay and in any event within 72 hours of the manufacturer becoming aware" | REQ-04: awareness + 72 h. |
| Art. 14(2)(b) contents | "general information, as available, about the product … the general nature of the exploit and of the vulnerability … any corrective or mitigating measures taken, and corrective or mitigating measures that users can take … how sensitive the manufacturer considers the notified information to be" | Model C notification: product fields, `vulnerability.description`, `exploit.description`, `mitigations.taken`, `mitigations.for_users`, `sensitivity`. |
| Art. 14(2)(c) contents | "(i) a description of the vulnerability, including its severity and impact; (ii) where available, information concerning any malicious actor …; (iii) details about the security update or other corrective measures" | Model C final report: `vulnerability.description`, `severity`, `impact` required; `malicious_actor` optional; `fix.*` required. |
| Art. 3(42) | "'actively exploited vulnerability' means a vulnerability for which there is reliable evidence that a malicious actor has exploited it in a system without permission of the system owner" | REQ-02: a person decides at triage; the system never infers it. |
| Art. 14(8) | "After becoming aware … inform the impacted users … where appropriate in a structured, machine-readable format" | Model C user advisory: no deadline, JSON draft. |
| Art. 13(17) | "manufacturers shall designate a single point of contact … including in order to facilitate reporting on vulnerabilities" | REQ-01 intake (cited in the reports). |

## Findings

### Finding 1: the final-report clock can start too late (needs action)

Art. 14(2)(c): the final report is due "no later than 14 days after a **corrective or
mitigating measure** is available". Our spec (REQ-04, Model D) starts the 14 days only from
`fix.available_at`, which the spec describes as a fix. If a mitigation (a workaround or
configuration change) is available before the fix, the legal clock has already started,
while our system still shows `awaiting_fix` and later a due time that's too late.

**Proposal (open question Q8):** define `fix.available_at` as the time the first corrective
**or mitigating** measure became available, and say so in `docs/spec.md` and
`openapi.yaml`. No code or schema change is needed. Shared spec, so Team 21 must agree.

### Finding 2: Model C can block recording a timely early warning

Art. 14(2)(a) requires the Member States only "**where applicable**" ("on the territory of
which the manufacturer is aware that their product … has been made available"), and asks
nothing about product versions. Model C requires `member_states` and
`product.affected_versions` before an early warning can be recorded as submitted. Within 24
hours a manufacturer may not know either. The system wouldn't stop them from filing with
ENISA, but it would refuse to record the filing, leaving a gap in the evidence trail.

**Options (open question Q9):** keep the strict rule (Phase 2 chose to require fields over
the regulation's "as available"), or let an early warning be recorded with those fields
explicitly marked unknown. Shared spec, so Team 21 must agree.

### Finding 3: exact hours are conservative (no action)

The CRA doesn't say how its periods are counted. Our rule, exact elapsed hours with no
adjustment for weekends, holidays, or daylight saving, produces the earliest reasonable
reading of each deadline, so it errs on the side of reporting early. The report should
present it as a deliberate simplification.

### Finding 4: "becoming aware" is defined by guidance, not the regulation (supports our design)

Neither the articles nor the recitals define when a manufacturer "becomes aware". The
Commission's guidance of July 2026 says awareness begins once the manufacturer has "a
reasonable degree of certainty", after an initial assessment if needed, that exploitation
has occurred. We've seen this only through law-firm summaries
([Browne Jacobson](https://www.brownejacobson.com/insights/cyber-resilience-act-reporting-obligations-in-force),
[CMS](https://cms.law/en/aut/legal-updates/ready-respond-report-the-cyber-resilience-act-s-reporting-regime-is-here),
[Hogan Lovells](https://www.hoganlovells.com/en/publications/eu-cyber-resilience-act-preparing-for-vulnerability-and-incident-reporting)),
so cite it as Commission guidance, not as the CRA. It supports REQ-02's design: a person
records the awareness time, which can differ from the receipt time (Model D E1 versus E2).
It also partly settles the Phase 1 pod disagreement in Team 21's favor (the clock starts at
reasonable certainty, not first sight).

## Assumptions confirmed as deliberate

These differ from the literal text on purpose, and Phase 2 (Q3.3) already documents them.
The text confirms they're conservative:

- **All three reports are always required.** The text allows skipping the notification and
  final report "unless the relevant information has already been provided".
- **Every notification field is required.** The text says "as available".
- **A fix released before awareness starts the 14 days at awareness (E5).** Read literally,
  "14 days after a … measure is available" could fall before the manufacturer even became
  aware.

## Fallback

Phase 2's fallback for this risk was to list our assumptions. If the pod doesn't adopt
Findings 1 and 2, the report should list them as known differences from the regulation,
with the reasons above.
