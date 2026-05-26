# Agentic Development / Testing Loop

```text
do {
    result = step();
    done = verify(result);
} while (!done)
```

Software development has largely operated on a [development/testing](./traditional-feedback-loops.md) loop since the beginning of its inception.  It is the fundamental loop that allows us to achieve our goals.  Try something.  Did it work?  Yes -> Great, No -> Keep trying.

In our day to day, we may experience this as changing some code and checking to see if the API is still returning the wrong results.

Agents operate the same way.  First build, then verify.  We know what happens when developers throw code over the wall, don't let your agents do it.

We model our agent behavior after our own, [I am the exemplar](../philosophy/i-am-the-exemplar.md).

## The Goal: tight feedback loops

The long-term vision of harness engineering should be to create extremely tight feedback loops between agents that build and agents that verify or evaluate.

If we build out an entire feature set that is thousands of lines of code before we do any verification, we have historically been apt to realize a mistake along the way which would fundamentally challenge our approach. This is costly. The tighter the feedback loops, the more productive we became.

Agents thrive on tight feedback loops.

* Make some changes
* Does it compile?  No -> Fix it
* Does it lint? No -> Fix it
* Do the unit tests pass? No -> Fix it
* Do the integration tests pass? No -> Fix it
* Does it **work**? :thonking:  Can your agent [verify what it built works](./agent-verification.md)?  No -> Fix it

At this point, our agents aren't able to handle extremely low latency real time operations.  They aren't cross referencing workspace level LSP type checking hints with the code they just wrote.  Maybe some are, but the agents aren't built to take in an event stream (this may be cost prohibitive based on how token caches work).  They're built to take in large blocks of context.  But that doesn't mean we can't aim for the same experience.

### Pondering about agent tooling

* Can we write an application that debounces all of the feedback, collects it, and relays it back to the agents?
* Can we write an application that generates test fixtures for all of the various scenarios your application may see?
* Can we make an agent that builds the applications listed above?
* Can we build an agentic harness that helps keep the agents on track by using agents to build these useful agent tools?
* Can we task an agent to build an agentic harness that enables all of these cool things?  [No, you cannot](../philosophy/ai-cannot-harness-engineer.md), agents are not capable of higher level thinking like that

The question of whether or not agents can [self manage and iterate on their own tooling](./agent-managed-tooling.md) is one I am currently exploring.  My efforts have been unsuccessful so far, but I will not give up.

I'm excited to see what new tools come that will aid in agentic development.

* Error telemetry pushed from application into a local service that manages the information and injects it into the appropriate agent terminal process
* Automatic scaffolding of APIs into markdown files for agent consumption (where agents are not trained to know the API internally)

There are so many interesting ideas to explore!

### Our modern development tooling

We seldom realize how spoiled we are when working in systems that have hot module reload capabilities. These tools have been designed around the philosophy that humans work best with extremely tight feedback loops. The longer it takes between build and verify, the slower the engineers work. This is a human engineering concept that also applies to agents.  LSPs offer immediate feedback on code that fails linting rules or type-checking.  It is quite impressive how much we have built to achieve instantaneous feedback on everything we build.

How these translate to agent tools will be determined in the near future.

## Development

Getting an agent to write some code is trivial.  Anyone can do it.  Getting an agent to write the right code in a complex application is difficult.  This is one of the main focal points of harness engineering.  Everyone has the same question: "How do we get the agents to write code effectively in our system?" Ask yourself a different question, "How do we get humans to write code effectively in our system?" but ignore the [grim trajectory](./grim-trajectory.md).

* **LLMs and Humans are extremely similar**: What makes humans more effective is very likely going to overlap with what makes LLMs more effective, you can't go wrong if you optimize for human efficiency (DX)
* [Documentation optimized for skimmability](./readability-equals-skimmability.md):  Agents are nearly identical to humans who start a project on their first day, they can't learn your entire system and you don't want them to reverse engineer the entire thing, so you must have documentation designed to provide all of the answers
* **Fundamental software / application principles**:

## Testing

Getting an agent to test code is difficult.  So difficult that in many cases people aren't even doing it.

### Testing can be avoided

Open up the application, *it looks good, ship it*.  It's that easy.

### Testing can be hard

In the beginning, everything is easy.  

The software is simple because it doesn't do much.  You can test the entire application by logging in and pressing three buttons.  Over time, more functionality gets added, more systems get integrated, more complexity emerges.  The industry standard is to press on the feature pedal until the tire treads completely wear.  Flat tire?  Keep on going, one more mile!  Maintenance is deprioritized, bugs start to emerge as new developers are added to the project and are changing systems they don't understand.

"How do I test this?" is cliche in the industry.  Sometimes it is very hard, but it shouldn't be

"How does my agent test this?" is the question that is blocking every agent focused dev loop.

### Tight feedback loops and test data
