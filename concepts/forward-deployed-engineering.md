# Forward deployed engineering

I imagine myself sitting in the office or building of my client, building features out with them.  They tell me what they want to do, I feed it into the prompt, it whirrs and spins and tokenizes and plops out the code.  It works.  Ship it.

The problem is solved directly in front of the user.

## Optimizing time to market

Historically, development took a long time, a lot of careful planning, a lot of thought, and was laced through process.  Measurements like cycle time emerged as popular ways to tell how fast ideas were turned into reality.  Books like Lean UX set the standard for constantly iterating on software to maximize action on user feedback.

LLMs allow us to condense the work down so small that it can be done in real time.

It's not new to be able to change an application in front of someone.  Many of us developers have been so well tuned into our application that we can make changes and adjustments over a video call.  We've been enabled by [hot module reload and extremely tight feedback loops](./traditional-feedback-loops.md) via developer tooling for nearly a decade.  What has changed is simply the **scope** of what can be attained in near real time.

## Sacrifice

If forward deployed engineering is all about delivering value to the user as fast as possible, it doesn't need to concern itself as much with other aspects of the software, such as maintainability, extensibility, or readability.  Those architectural properties can ebb and flow.  The [harness engineer](./harness-engineer.md) and the modern software engineer can [refactor](../application-architecture/tech-debt.md) it later, as long as nobody [builds on top of the slop](../application-architecture/tech-debt.md).

Consider it a temporary sacrifice for immediate value, a short term loan if you will.

## Evolution of the role

If FDEs are to be compared to Vibe Coders, then FDEs are apt to come from anywhere, not just a software engineering background.  Where I think the most talented FDEs will come from:

* Technically adept product owners and project management
* User focused engineers who understand how to build the user experience (aka Product Engineers)
* Well tenured software engineers (tech leads, architects, etc)
* Anyone who is tech savvy and can steer LLMs to write code that solves problems (this is a very large pool of people)

The people working in the product space are likely to become FDEs very quickly.  We hear a lot about CPOs vibe coding and getting a lot of business value.  They are empowered to do this, and they should be acknowledged as [part of the team](./team-of-the-new-era.md).  Product engineers may also embrace this space, with a specialty of being able to act swiftly and work within the harness more effectively, resulting in fewer invariant violations.  Well tenured software engineers are likely more apt to segue into harness engineers or stay within the zone of solving complex problems with their strong system design skills.
