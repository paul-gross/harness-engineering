# Grim trajectory

In my experience, most technology organizations and software groups are generally in the same positive feedback loop due to excessive feature development focus.

Applications are built, they start small.

* Features are added
* Implementation time for features increases over time as unmanaged macro level complexity grows
* Business adds more developers to compensate for decreased feature velocity
* Additional developers add significant overhead
* The application becomes harder and harder to change

Eventually, developer churn leads to feature velocity seizing and organizations shifting to significant support mode.

This is caused by a number of things, but the main reasons are as follows:

* Lack of engineering talent (it's so rare people do not understand how to find it) who understand how to manage macro level complexity
* Lack of understanding of who has talent leads to not giving the right people ownership and authority
* Building on top of tech debt (note that it's only debt after you build on it)
* Leadership dictating timelines and scope and developers not caring because they have no stake (they can just quit, why would they care?)

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

**This is the grim trajectory**: We have no reason to believe that the standard lifecycle we experience year after year will change with the addition of LLMs or Harness Engineering

## How do we get out of the grim trajectory?

If you are a leader and you don't have talent, hire an [Application Architect](../concepts/application-architect.md) and give them some autonomy.

If you are a leader and you do have talent, **get educated on what it takes and help to educate your talent**.

If you are talent, but your leader is singing the Death March tune, point them here or move on to where your talent is understood.

For the practical, phased way out, see the [Brownfield guide](./brownfield-guide.md).
