# Lift

Lift is the force you feel that will push you towards merging or releasing LLM generated code that you either have not reviewed or do not understand.

## What you will feel

In a more optimal workflow, a developer will task agents with larger features that bake for longer and write more code autonomously.  It will become simpler to maintain two or more agentic workflows in parallel.  As one is working on a task, the developer is reviewing the work of the other, iterating on it, and verifying it.  It may seem daunting at times.  You've just finished reviewing series of commits spanning 1000 lines of code, you've verified the change manually, and you've iterated on the code to maintain the integrity of architecture of the application.  Now you do it all over again.  And again.  And again.

The most optimal workflow isn't glamorous, it's quite taxing.

Some of these tasks may be large refactors that move code around, update import statements, and have no changes to the application logic.  The tests were not changed and they still all pass.  But there is still 1000 lines of code to review.

You've done these before, and in all recent cases, the generated code was **fine**.

You are faced with a decision.

* **Trust it, it will be fine**: If there is a bug, it'll be found, and you feel strongly that your time is better spent setting up the next prompt
* **Review every single change**: No trust, comb through it

This is the smallest unit of lift I have encountered.

## Getting air

Stronger forces of lift will occur when you are building new functionality rather than doing routine codebase flossing.  The agents will build new systems, new abstractions, new classes, new projects, new screens, new database tables, etc.  The list goes on forever.  When these agents work on their task, there is always a chance that hallucinations occur or that the agent simply missed the mark.  Much like AI generated art, when you look at the details they can often seem correct at first glance but then become obviously wrong when looked at with scrutiny.  Maybe there is an arm with no hand, or a cup whose handle is a finger.  It's much easier to scrutinize an AI generated image than it is to scrutinize 1000 lines of systemic changes throughout a codebase.  It's also easier to describe the concept in how it manifests in imagery than it is to describe the concept in how it manifests in code.

These defects in the code are a form of drift.  If you allow the faulty pattern to enter the codebase, it will inevitably become the model for some other task that an agent takes on.  It may spread throughout the codebase, infecting it like a cancerous cell.

Vibe coding is in essence when you are getting air from the very beginning.  There is no evidence to support that getting air is good or bad at this point.  Our hunch is that the spiral of increased complexity will continually slow down the agents and lead to increased time spent iterating, reviewing, and validating the output (decreased feature velocity).  This is remarkably similar to the pre-LLM era where inexperienced developers and teams were left to push changes without adequate review or architectural consideration.

Getting air is not necessarily the same as accumulating tech debt, tech debt occurs when you build on top of something.  Getting a little air is akin to having imperfections in the most outer concrete layers of your application (frontend HTML).  It's not ideal, but nothing depends on it, so you can clean it up pretty easily at any point.

## Lift and getting air is not inherently bad

Strong agentic development architects will recognize the value in getting new functionality to the users.  With LLM generated code, this process can occur [at the frontline](./forward-deployed-engineering.md).  There is no business out there that doesn't want to get features out yesterday.

As the codebase drifts due to engineers pushing code they have not reviewed or do not understand, it is simply a matter of prioritizing the process of regular flossing and maintenance as pattern of the software development process.  The [Grim Trajectory](./grim-trajectory.md) and [FDEs](./forward-deployed-engineering.md) are counterbalanced by the [Agentic Harness Architect](./agentic-harness-architect.md)).


