# How we tested the README

The audience was a first-time Codex user. The job was to run the skill on supplied offers, understand its decision, and find the inputs needed to check it.

## References that changed the example

| What we inspected | What we used |
|---|---|
| Trail of Bits’ Goal Prompt pairs a request with the command its skill returns. [Example](https://github.com/trailofbits/skills/blob/07bce8a2c8ccc56c5b44b7067a04b8bf46128f05/plugins/goal-prompt/README.md#example) | Put a copyable prompt immediately beside the venue decision it produced. |
| Vercel Optimize describes recommendations it holds back when the evidence is insufficient. [What you get](https://github.com/vercel-labs/agent-skills/blob/3296353bb7fff11269fff02e717350f05b721331/skills/vercel-optimize/README.md#what-you-get) | State why each offer fails and the precise change that would make Garden Center eligible. |
| Frontend Slides lets readers inspect finished work in its gallery. [Included styles](https://github.com/zarazhangrui/frontend-slides/blob/9906a34d640d2111f724544cbc50f7f130569ae1/README.md#included-styles) | Show the calculation and verdict on the README page itself. |
| Planning with Files names the artifacts readers will use. [README](https://github.com/OthmanAdi/planning-with-files/blob/51bf62def62d1cb317d37936929b4ef97cf862c3/README.md) | Name and link the exact offer sheet alongside the prompt. |

We also inspected the [Spec-to-Code Compliance verdict definitions](https://github.com/trailofbits/skills/blob/798b591aa498100f7744a948c0e3cbfc40e7eded/plugins/spec-to-code-compliance/README.md#verdicts). Its treatment of partial findings reinforced the decision to explain each verdict. Four references supplied four distinct choices, so we stopped there.

## What the skill returned

A fresh solver received the revised skill, the [fictional offer sheet](venue-offers.md), and the prompt in the [README example](../../README.md#example). The earlier skill validation had also found no qualifying venue. The new run produced the following answer from the published inputs. [Earlier validation](../../solve-with-evidence/references/validation.md)

> **None of the three offers meets all requirements.** The 45 printed packets cost $54 ($1.20 each).
>
> | Venue | Total with packets | Decisive evidence |
> |---|---:|---|
> | Oak Hall | $454 | Seats 50 but lacks step-free access. |
> | River Room | $354 | Has step-free access but seats only 40, five short. |
> | Garden Center | $629 | Seats 50 and has step-free access. The $500 room, $75 required setup and $54 for packets put it $29 over budget. |
>
> Choose Garden Center if it reduces its quote by at least $29 or the budget rises to $629.

The organizer set a hard $600 cap. The public example keeps it fixed and describes a reduced quote as a condition. At $28 off, Garden Center would still cost $601. At $29 off, its total would be $600.

## Fresh-reader check

Two separate Codex agents started with empty conversation histories. Each saw the same question and only one version of the README. Neither saw the rubric, solver conversation, other reader’s answer or linked files. The question was:

> Read the README as a first-time Codex user. From the README alone, explain how you would install and invoke the skill, what you would tell the workshop organizer, the evidence for your answer, and which source you would open to check the inputs. Mention anything you could not determine.

We defined six checks before either reader answered.

| Check | [Previous README](https://github.com/Emuthmartinez/solve-with-evidence/blob/edbbaf8f78256660d74328540d8cdf6d46eba991/README.md) | Revised README |
|---|---|---|
| Gives the Codex installer and correct skill-folder URL | Pass | Pass |
| Starts a new chat, invokes the skill and supplies the offers | Pass | Pass |
| Concludes that no supplied offer qualifies and keeps selection open | Could not determine eligibility | Pass |
| Identifies the decisive constraint for each offer | No figures or quotes on the page | Pass |
| Computes the $54 printing cost and the $29 boundary | No inputs to calculate either | Pass |
| Names the source file to open for the original offers | No file identified | Pass |

The first reader correctly declined to infer a decision from the missing inputs: “I can’t recommend a venue from the information here.” The second reader said to “keep looking and ask Garden Center whether it can reduce its quote by $29,” reproduced all three totals, and named `evaluations/readme/venue-offers.md`. The result was 2/6 and 6/6 on this document-comprehension check. Both readers were AI agents. They described the installation steps from the README. The published package installation was checked separately.
