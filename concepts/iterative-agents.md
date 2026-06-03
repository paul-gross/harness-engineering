# Iterative agents

A single agent pass may only get us 60% of where we want to be.  Running agents iteratively against a goal gets us closer and closer to that 100%.

## One-shot fallacy

In 2025 and early 2026, the goal of many developers was to create enough context for a single agent to one-shot a solution to a prompt.  We had marketing pushing this on us, showing videos of agents building entire applications.  The practicality of it was near-zero, but it generated a lot of hype.

The one-shot mindset has too much drift.  It's going to create *something*, but it will be more of a slot-machine pull than we may want.

The real path forward was dividing the greater parts of the whole of software engineering and applying agents to the task.

## Managing context and goals

When we utilize a single agent in a conversation, we want to manage our context (what we know) and our goals (what we aim for).  The context should contribute towards guiding the agent to reach that goal.  If our goal is too large (Build an entire application), the agent will require context of many dimensions.

* What is the business domain of this app?
* How do I build a React app?
* How do I build a backend?
* How do I deploy this app?
* What kind of architecture do I use?
* What kind of developer tooling do I set up?
* ... How do I unit test this one function?

This high level goal has too many pieces.  We cannot expect a single agent to do all of these pieces to our expectations.  It usually doesn't, and that results in inefficient iteration on the model output.  To remedy this, we could either break the problem down into smaller pieces or we could lean into our expectation that the agent will not fully achieve our goals.

### Iterating on a goal

In the above example, iteration is achieved by setting up policy and agentic processes.  The policy is the guide that the agents use to determine if the goal is met.  The process is the guide for how to apply iterations to achieve that goal.

### Policy

Any technical taste or invariant that we expect from the agent can be established as a standard, convention, or technical requirement inside of a technical document.  Any business invariants can live along side those technical invariants.  These policies are objective and factual -- they are either adhered to or they are not.  These policies can include anything from linting rules to agent facing markdown files.

What's important about policy is that it guides LLMs to know whether the goal is met and what needs to happen for that goal to be achieved.

### Process

The single agent pass in a typical coding harness will include research, development, testing, and verification.  This is the most basic and least opinionated coding harness capability (as of spring of 2026).  Building processes around this is up to the harness engineer.  We can state to an agent to build the *target* using *a specific process* and it will follow the track laid on it.

* [Development / Testing Loop](./agentic-development-testing-loop.md): One agent implements, the same agent verifies via tests or agentic verification
* **Development / LLM Code Review**: One agent implements, a separate agent reviews the output against the policy
* **Harnessing / LLM Context review**: A human or agent adjusts the harness, a separate agent reviews the policy against the [canon](./harness-components.md) and tests the harness using evals

We can establish more process and policy to guide the agents towards our goals.  It need not be limited to development efforts alone either.  An agent could be tasked to release the software while another agent is tasked to evaluate if the software has been released.  An agent could validate a business plan against market research.  An agent could evaluate timeline expectations against scope and resource allocations.  

## Separation of specialty

Within each process we can narrow our agent's agenda to be more specific in an effort to maximize the value of the result.  A code review may consist of checking for completeness, correctness, and adherence to standards or architectural taste.  By splitting the code review up into three separate agents, they can each hone in on the context that is relevant to their concerns and judge more accurately.

The first iteration does not need to have the full context of every aspect of the system (architecture, security, user personas, et al).  Specializing the first pass on the highest level of architectural scaffolding can save us a lot of wasted tokens.  We may be off the mark, but our process will iterate and move us towards that goal.
