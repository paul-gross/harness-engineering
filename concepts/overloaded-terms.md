# Overloaded terms

Architecture.  What does that mean to you?  It probably means something different to the agent.

## Overloaded terms in Software Engineering

If you ask 1000 developers what architecture means to them, you'll get dozens of different definitions.  But if you ask how many times a developer hears the word, architecture, they'll tell you dozens of times.  This is the biggest offender of overloaded terms that I can think of, so it's the greatest example to provide here.  Use of overloaded terms often leads to different trains of thoughts in different people in the same conversation.  This has troubled the industry for a long time.

What is architecture?  *It's the important stuff* So why do we expect agents to understand what we mean when we say "you are an architect?"  **You are good at the important stuff**.  What does that even mean?

When we talk to an agent, should we expect the agent to really understand what we are talking about when we are talking about creating worktrees?  I think the answer to that is no.

* Worktrees are a fundamental feature within Claude Code
* The claude code system prompt surely has references to worktrees and an opinionated set of prompts describing aspects of them
* Any attempt at retraining the agent to use a polyrepo multi-worktree workflow *immediately* suffers from friction

Special care should be taken to create a clean slate for definitions for AI (and often humans too).  Sometimes we may need the equivalent of a CSS Reset.

## Thematic aliasing

LLMs and humans are remarkably good at understanding aliases.  If the aliases build on a theme, they can convey a link between them just by their name.  An alias is a word that is meant to mean another word, often to distinguish itself from the perceived meaning of said word.  Imagine that we want to customize the behavior of how teams work in Claude Code.  We'll describe what we want the agent to do when we tell it to "spin up a team."  But the agent is already predisposed to think that a team means something completely different.  So when we say "spin up a team," it will spin up an internal set of agents (inherent claude code functionality) just as likely as it is to do any instructions we tell it to do.

Maybe our core product is called "Teams."  You can imagine the frustration of working with an agent who spins up teams every time you ask it to send a message to your coworker...

An example speaks for itself

* **Winter**: The name given to my workflow so I can then refer to it by name and the agent unmistakingly targets the workflow itself rather than the code
* **Blizzard**: The name of the custom process used to spawn multiple agents (a team) and coordinate work based on our custom workflow
* **Snowflake**: The name of the leader / coordinator of the blizzard

This achieves the following:

* **Related Concepts**: The context (Winter, Blizzards, Snowflakes) is tied together and linked through the natural meaning of those words
* **Clarity**: The aliases provide an unambiguous and extremely clear way of directing communication about a topic
* **Reset meaning**: The aliases remove the overloaded terms and redefine the concept from the ground up.

## Honestly, why?

Because when I asked the agent to spin up a team, it more often than not created a subagent that ran in-line with a new context but inherited the default model.  But when I started saying "Create a blizzard," it would read the Blizzard Skill and spin up a multi-agent team 100% of the time.
