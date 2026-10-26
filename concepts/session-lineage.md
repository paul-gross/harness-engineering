# Session lineage

Agents traveling graphs is the current direction of [Harness engineering](./harness-engineering.md) and session lineage is how [coding harness](./harness-components.md) sessions map to that.  While agents travel between nodes, we have the opportunity to pick what context is relevant to the node and share it on that agent's journey.

Session lineage is the selection of previous context for a given task within the journey of fleet orchestrated agents.

## What?

Session lineage is the idea that two different steps in a software assembly line can share the same coding harness session, and thus share context.  At each node of the graph, agent configuration isn't just the model, the effort, and the prompt - it's the memory too.

In a software factory based on graphs, the build agent can hand the output artifacts to a [cold review agent](./agent-verification.md).  The review agent doesn't see anything about what the build agent knows.  It only knows what was produced.  This keeps the review fair.  That review, should it fail, could [travel back](./iterative-agents.md) to the build node and resume that session.  Is it better to fix the review findings with a fresh agent that has no context?  Or is it better to resume the build step's session?

In some cases, we can explore this with data, experiments, and evaluations.  The [build and review cycle](./agentic-development-testing-loop.md) can get pretty complex, so it's a tough optimization problem to approach.  Instead, consider something more simple:  The review passes, verification passes, and the final step before creating the pull request is to rebase or merge in the latest main branch.  Should merging the main branch and resolving conflicts use the same session as the build step?

Starting fresh:

* Smaller context windows result in reduced cost and less context poisoning
* Removes bias from previous context, but removes context about the original implementation

Resuming the session:

* Potential to minimize or eliminate repeat inference
* Provides optional optimization by ephemeral artifacts

## Why it matters

Resuming a context window with a partially related task imposes an input token cache tax.  The cache could be stale which would result in an input token receipt for the whole conversation that may output only a dozen tokens.  In my own assembly line, the [pre-push step](https://github.com/paul-gross/winter-workflow/blob/master/skills/pre-push/SKILL.md) carrying the context of the build step resulted in a 281:1 ratio of input cache tokens to output tokens.

I opted to start the pre-push context fresh.  I saw no noticeable difference (no quality data to support it) so that became a cost savings that has assumed no loss of quality.

## Cold eyes

Any time we spawn an agent, we should apply the concepts behind the single responsibility principle.  The agent should have one job, or one reason for being.  It should carry with it only the context and effort tokens related to its own agenda.  

One agent = one agenda.

One agenda = one slice of context related to its goal.

Agents that write code should focus on writing the code that solves the problem that is presented to them given the [plan](./iterative-planning.md) they must adhere to.  They don't need to understand everything that went into that plan.  Just the same, an agent reviewing the output, iterating on it to improve it, needs only to understand the review criteria and the code artifact itself.

## What carries intent instead

Give the agent [reference data](./progressive-disclosure.md) to support any information needs it may have.  Give it access to the work item descriptions, the original plan, the commit messages, the diffs, the findings, and any other tangible artifact that can be solidified along the journey.  

## The dead end

The bet I made in July of 2026 was that reusing the context from the build step in the pre-push step would enable a better merge conflict resolution.  The cost data said otherwise.  Rebasing and merging didn't require the effort and thoughts of the build, it only required the artifacts that were stamped along the journey.  Those artifacts serve as the compacted conversation of the graph.
