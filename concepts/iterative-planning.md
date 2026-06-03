# Iterative planning

An overwhelming amount of people have adopted planning as a critical part of their workflow.  It's profound how the entire industry seems aligned on it.  We can't type in a short prompt and expect the agents to work for hours while we sit back and watch YouTube videos on our second monitor.  I wish it were the case, but [prompt to plan to commit drift](./high-level-thinking-drift.md) works against us.  Planning will always be a component of engineering, no matter how advanced your harness is.

## Inline planning vs Iterative planning

In a basic AI assisted terminal development workflow, the user may build the plan with the agent within the conversation.  The plan is a simple markdown file and the process is baked into the coding harness.  Once the plan looks good to the developer, the context is cleared and work begins.  This is **inline planning**.

Once the scope of a unit of work exceeds a single conversation, an in-line plan is no long adequate.  That plan is ephemeral and it is no longer available.  The [second agent](./iterative-agents.md) may not understand the goals.

Iterative planning treats the goal as an artifact.  It can be a markdown file, a Jira ticket, a GitHub issue, or an HTML file.  That artifact is carefully modified by the user and refined.  Now we can have multiple agents work on that artifact sequentially or concurrently.

### Business plans, technical approaches, phased development

When we shift to iterative planning, we can start to create artifacts that are not just a single file or markdown file but instead a suite of information for the agent to consume.  These can be preserved after the fact and used to update product documentation or used for historical reasons (retrospectives for feedback).

My preferred suite looks like the following:

* **Business plan**: A non-technical document describing what we will build, why, and what the acceptance criteria is
* **Technical approach**: A high level document showing contracts, interfaces, domain models, and workflows (no code)
* **Phase documents**: A set of broken down individual pieces of work that contribute to the greater whole

Each layer of artifacts builds on the previous layer.  The technical approach is anchored to the business plan.  The phase documents are anchored to the technical approach.  When one changes, it cascades.

## Iterating on an artifact suite

Have a conversation with an agent about the plan.  Scrutinize the details, eliminate the drift, and pare it down so that it is concisely what is necessary.  The typical LLM will embellish product details with hallucinations.  It is always important to prune those out before work starts.  It is much easier to eliminate phantom acceptance criteria that is a single bullet point in a business plan than it is to assess what is wrong in the final code review.

Commit the artifact.  Keep it.  Put it in Jira or source control.  People can look back at it to understand what you did and why you did it.  Agents can evaluate the final output with the original artifacts to dig for product / planning harness improvements.
