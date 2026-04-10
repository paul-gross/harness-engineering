# Application Architects and Harness Engineering -- The Agentic Harness Architect

This new era of software development has new emerging skills that are needed.  They may overlap with traditional software development, but I think it is very likely the case that we will see a new role emerge.

It happened with DevOps, it happened with forward deployed engineers, it'll happen with whoever is responsible for the agentic harness.  

## What?

I believe that a strong & talented application architect operating with some level of autonomy has been an important part of controlling macro level complexity in software for years.  Additionally, I feel a new skillset is emerging, harness engineering, which is an extension to the application architect.  A harness engineer probably needs to be an application architect, but not all application architects are harness engineers.

There is too much overlap between human developer productivity (largely affected by the application architect's decisions) and LLM productivity.  You cannot wrap a harness around a giant spaghetti monster and expect results.  It's the same as if you tried to wrap a process around a failing team.  Technical Excellence is still the foundational piece.

The Agentic Harness Architect is the superbuilder (superbuilder term *coined* by Coinbase CEO, get it, coined, haha) that can keep an operation like [Gas Town](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04) running without layers of insurmountable spaghetti code and manage its macro complexity.  **This is incredibly hard**.  It requires intelligence, a strong skillset in software engineering, an intuition for big picture thinking, and a fast-learning mindset.  They need to be able to come up to speed with things quickly.  

Steve Yegge said it, "most people can't read."  You need to be able to read, and you need to be able to read exceptionally fast. It's all about how fast you can *learn*.  I don't mean skimming.  I'm talking about full understanding and comprehension of what is going on.

* This role [cannot be replaced by an LLM](../philosophy/ai-cannot-harness-engineer.md)
* [Iterative Planning](./planning.md) cannot be removed from the agentic workflow entirely
* Positive feedback loop experiments, such as [Forward Deployed Engineering](./forward-deployed-engineering.md) become more efficient

## How?

The codebase should be like a superconductive magnet for a high speed maglev train system. The term I love to use is they continuously identify and eliminate **friction**.

### Architecture & organized code (Application Architecture)

* Maintain incredibly useful and powerful abstractions that support application use cases
* Eliminate wrong abstractions, plug leaky abstractions, separate concerns
* Reorganize concepts and structures within the codebase to maximize how easy it is to extend the code and review changes
* Maximize testability and maintainability without sacrificing other runtime architectural concerns
* Provide and maintain Exemplars in the codebase for agents to follow
* Provide guidance and solutions to problems that the primary agentic developers encounter when constructing larger new systems 
* Create computational checks and inferential LLM prompts that autonomously reduce drift

### Steering the agents (Harness Engineer)

* TBD

In some analogies, the human is described as *steering the agent*.  I don't love the analogy, but I think it holds.  The analogy I like to use is the [walk-run-rocket-into-space](./walk-run-rocket-into-space.md) analogy.  The agentic harness architect is responsible for building a rocket boosted development capsule that stays grounded and doesn't [lift](./lift.md).
