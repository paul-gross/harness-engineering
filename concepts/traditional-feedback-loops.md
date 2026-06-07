# Traditional feedback loops

How we worked when we wrote code by hand.

## The traditional development and testing loop

Everything that agents do in order to build software strongly mimics what we have done as engineers in our day-to-day. One very basic example is our basic [development and testing loop](./agentic-development-testing-loop.md).

As an engineer, I would often write software on one screen and visually verify the software on another screen. Or I'd verify it using a tool that hit an API endpoint. Or I'd verify it using unit tests. We have to assume that agents must follow a similar path, but those tasks are much more complex than simply writing code. They require an iteration process — make some changes, verify, repeat. These small loops are part of the way we have worked.

## The long-term vision

The long-term vision of harness engineering should be to create extremely tight feedback loops between agents that build and agents that [verify or evaluate](./agent-verification.md).

## Why tight loops matter

If we build out an entire feature set that is thousands of lines of code before we do any verification, we have historically been apt to realize a mistake along the way which would fundamentally challenge our approach. This is costly. The tighter the feedback loops, the more productive we became.

We seldom realize how spoiled we are when working in systems that have hot module reload capabilities. These tools have been designed around the philosophy that humans work best with extremely tight feedback loops. The longer it takes between build and verify, the slower the engineers work. This is a human engineering concept that also applies to agents.
