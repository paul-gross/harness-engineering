# Agent-managed tooling

Can we automate the creation and management of the proprietary tools we scaffold to help us develop?

## Exploration mode

I have been exploring this in my own work and at my professional job.

Agents thrive on tools that deterministically achieve their goals.  There is a difference between spelling out the tools that they will build for themselves and spelling out the expectations that coerce the agents to build things themselves.  I've seen a lot of success in the former, and moderate success in the latter.  As the models improve, they gain more understanding of how to self-manage.

The first idea I am exploring is creating a verifiability matrix within the harness along with a verification matrix within each plan.

### Domain harness: verifiability matrix

In the domain [harness](./harness-components.md), we can define an area that has an exhaustive list of ways that an agent can [verify](./agent-verification.md) an application.  This can include basic operations like building, testing, or linting.  This can include complex operations like accessing a local API directly, pushing messages on a local queue, or interacting with a local redis container.  The matrix gives the agents a guide on how to make sure the changes they make are working as intended.

When we add a verifiability matrix, the agents can use it ad hoc.  This doesn't guarantee they will use it, but it does help them understand the processes and methods at their disposal.

Give the agents a wide range of ways to verify the changes that they implement.

### Planning: verification matrix

In the [planning stage](./iterative-planning.md), the verification matrix is the artifact that is stamped out that agents use when looking back and understanding how to verify the changes they've put in place.  It's a list of pieces of acceptance criteria, each correlated with an identifier of how it will be verified.  The verification matrix references the domain harness's verifiability matrix.  It connects the business requirements of the change to the technical agentic or deterministic verification process.

This verifiability matrix can be used in the planning phase.  For each piece of acceptance criteria, we can note the method of verification.  We can build our planning phase out to identify acceptance criteria with no means of verification.  This can signal to the agent that we must **build a new method of verification** or **extend the existing verification tooling**.

### Execution: the verification step

If we have the sibling matrices established, the agent that is executing and implementing changes at the code level can now go back and reference the requirements and the steps to verify them.  After completion, they know to check off each step and they know to use the tools referenced.  This establishes a very achievable goal that can be restarted or rerun after [multiple iterations](./iterative-agents.md).

