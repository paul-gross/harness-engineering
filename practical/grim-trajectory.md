# Grim trajectory

In my experience, most technology organizations and software groups are generally in the same positive feedback loop due to excessive feature development focus.

Applications are built, they start small.

* Features are added
* Implementation time for features increases over time as unmanaged macro level complexity grows
* Business adds more developers to compensate for decreased feature velocity
* Additional developers add significant overhead
* The application becomes harder and harder to change

Eventually, developer churn leads to feature velocity seizing up and organizations shifting to significant support mode.

This is caused by a number of things, but the main reasons are as follows:

* A culture where engineers change only what is necessary to check off the acceptance criteria (It works, but isn't right)
  * Can be the case if change is too hard (big ball of mud architecture)
  * Can be the case if risk of change is too high (lack of automated tests)
  * This can often have a snowball effect
* An overly optimistic emphasis on new capabilities and their connection to potential revenue
* An inability to objectively measure the true feature velocity of a team
  * It is hard to even understand if an investment pays dividends let alone convey it to leadership
* Lack of engineering talent within the team who understands how to manage macro level complexity as they go
  * Lack of understanding of who has talent can be the root cause
  * Lack of providing the right people autonomy, ownership, and authority can contribute to this
* Building on top of [tech debt](../application-architecture/tech-debt.md) (note that it's only debt after you build on it)
* Leadership dictating timelines and scope and developers not caring because they have no stake
  * Developers can move on to other projects or companies, they are not invested in the outcome

## Agentic Development does not change this

If we substitute agentic development (AI code gen) for traditional hand written code, we have no reason to believe the trajectory of software development will change.  There is nothing magical about LLMs that will suddenly change the business organization.

If we extrapolate what we know, we can imagine what the future would look like

Applications are vibe coded, they start small...

* Features are vibe coded in
* Agents experience more hallucinations as they struggle with macro level complexity growth
* Business adds more agents to compensate for decreased feature velocity
* Additional agents create new problems, more drift, more cost per feature
* The application becomes harder and harder for LLMs to change
* The token cost for AI exceeds the human cost to build manually

Eventually, context limits and macro level complexity exceeds what an LLM can reasonably work with and organizations shift to significant support mode.

**This is the grim trajectory**: We have no reason to believe that the standard lifecycle we experience year after year will change with the addition of LLMs or harness engineering.

## Signs you are on the grim trajectory

Warning signs to look out for in your organization to know if things are spiraling:

* Developers adopt tooling like Claude Code or Codex and utilize it to write code, but there is no feeling of improved pace
* Code reviews remain as a largely manual task and become the source of complaint ("All I do is review AI slop")
* Increased number of deployments that yield degradation or outages
* Developers are still working on one task at a time (not two)

Positive signs that developers are engaged and committed to improvements:

* There is more work in progress and new bottlenecks that they raise complaints about
* Developers are reporting that they are taking time to adjust their workflow
* Work in progress increases while cycle time stays the same, **throughput goes up**
* Large scale tech debt removal is occurring

## How do we get out of the grim trajectory?

If you are a leader and you don't have talent, hire an [Application Architect](../concepts/application-architect.md) and give them some autonomy.

If you are a leader and you do have talent, **get educated on what it takes and help to educate your talent**.

If you are talent, but your leader is singing the Death March tune, point them here or move on to where your talent is understood.

For the practical, phased way out, see the [Brownfield guide](./brownfield-guide.md).
