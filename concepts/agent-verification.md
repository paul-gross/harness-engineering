# Agent verification

Any given output of AI should be subject to verification.  We can choose to verify the output ourselves (human verification) or we can utilize AI to verify it on its own (agent verification).  Agent verification is the concept where a combination of deterministic and non-deterministic concerns are checked and the original output has feedback provided to it.

## Tools & agent verification

Without tools, the verification judgement will be entirely based on the LLM itself.  This has some value.  Tools augment, creating more value.  Tools that humans build into deterministic pipelines add significantly more value.  We can divide our verification into these categories:

* Pure LLM judgement using non-deterministic LLM processes
* Deterministic tool judgement using non-deterministic LLM processes
* Deterministic tool judgement using deterministic processes
* Human judgement

The pure LLM approach is by far the simplest to create but the most expensive to run.  The pure deterministic approach is the most complex to build and the cheapest to run.  Each has their own capabilities of judgement with different conceptual ceilings.  The human judgement is arguably the most costly, but it's difficult to prove that claim so I will leave that to the reader to decide.

## Embracing agent verification

Agent verification can be used on human created output or agent created output.  In either case, there is arguably an effectiveness in terms of the cost to value ratio.  It's simple and cheap to ask an agent to review code, review documentation, or review my essay on harness engineering.  It's a much bigger ask to push a human to do it.

Agent created outputs tend to fall short.  We often see an agent get most of it right, but it's not _quite right_.  It's missing a small detail or it added an unnecessary embellishment (this is why I can't use AI to write this [Digital garden](./digital-garden.md)).  Despite that, we can think of agent verification as a way to reduce the probability of an error, or reduce the probability of the unnecessary embellishment.

**Most importantly**, apply that same acceptance to agent verification itself.  Just as agent output falls short, agent verification **will fall short too**.  If agent verification gets us 80% of the way, _humans are responsible for the last 20%_.

### Areas where agent verification has value

* **Code review**: Agents can reason about the code and make judgements about complex concepts
* **Context review**: Agents can read supporting markdown files in a [Domain harness](./harness-components.md) and evaluate if they improve future agent work
* **Harness review**: Agents can evaluate the process of how agents have been working and make judgements about the agentic process itself
* **Using the output**: Agents can interact with output (test it) in a [local ephemeral environment](./local-ephemeral-environments-for-agents.md) to check if it works or not
* **Reading logs**: Agents can read logs and other observability metrics to check if scenarios occurred or not
* **Challenging the thought**: Agents can provide examples of counter-arguments or counter-theories to disprove

## Big unlocks along the way

Assume that the first step in the journey of [Agentic development](./agentic-development-testing-loop.md) is to prompt an agent to build a piece of software from start to finish.  If the agent is only able to write code, but can't run it, it will be flying blind.  The more [immediate feedback](./traditional-feedback-loops.md) it receives and the faster it receives it, the more likely it will correct.

* Give the agent a way to compile the application
* Give the agent a way to run the application
* Give the agent a way to set up test data to create specific test cases
* Give the agent a way to set up mock services to simulate scenarios

Sometimes it isn't about giving agents a way to do something.  Sometimes it's about telling the agent to do something.

* Instruct an agent to build deterministic test data generation tools
* Instruct an agent to build mock services with levers to create various scenarios

If we go further, we can project some future ideas that may provide value

* Model the agent to [manage its own tooling](./agent-managed-tooling.md) to generate test data
* Model the agent to manage its own tooling to mock services

And if we apply this more abstractly:

* Model the agent to manage its own tooling to achieve the level of verification we strictly define
