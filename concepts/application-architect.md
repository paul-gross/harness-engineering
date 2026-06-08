# Application architect

The codeowner.  The maintainer of rules, invariants, structure, and long term vision.  The one responsible for the architectural tenets that are set.

## What?

An application architect is the software engineer responsible for ensuring system longevity, low maintenance costs, and high productivity.  Somebody has to be responsible for it. If nobody is responsible and nobody cares, the system naturally becomes a [big ball of mud](https://en.wikipedia.org/wiki/Spaghetti_code#big-ball-o-mud).  There are countless articles, blog posts, and books about how to avoid increasing development costs and decreased feature velocity.  They all point to the overloaded term, [architecture](./overloaded-terms.md).  Leadership and management seldom understand architecture.  It's a different career path.  The individual contributor naturally segues into management, system architecture, or enterprise architecture, but there isn't as much emphasis on the application architecture.

Oftentimes application architecture is lost.

Application architects do not need to govern all system design, but they have stake in it.  System design is a skill that mid, senior, and staff engineers have.  Application architecture is different.  System design determines how the pieces interact.  Application architecture is how those interactions materialize in code.  While system design focuses on what needs to exist to solve a problem, application architecture focuses on what parts of each system are aware of other parts, how those implemented, and how to make sure it is testable, configurable, pluggable, and observable (and any other tenets the project requires).

## The default

If an organization is not putting a skilled, well-tenured application architect into the position as the technical lead on an application, somebody will always become that role by default.  Somebody on the team will make more decisions than the others.  This happens in a number of ways.

* They gain the respect of their peers and influence positively through strong relationships
* They produce more code, and thus encounter more decisions to be made
* They take liberties and push through conflicts or use political tactics (like forming a political gang to approve work swiftly)

The default person will likely be the team's most senior engineer.  In many cases, they are given the title of technical lead and feel empowered to do so.

A technical lead may not be a great application architect, and that is okay.  What is important is to acknowledge that the decision of who bears the responsibility should be respected.  Talent is costly and scarce.  Putting less tenured engineers in positions where they will act as the technical lead can be the only good choice the business can make.  It can also be the choice they feel is best based on their understanding of application architecture and its impact on the system as a whole.

## The untrusted, inexperienced application architect

Oftentimes the default application architect is a senior software engineer with only a few years of experience.  We've seen this all over the place.  These individuals are often told that they are expected to lead something.  But the details of what that means are left unsaid.  There is no written guide on how to do their job, they're just placed in the position and left to handle things.  People in these roles have often told me, "I was put into this position and nobody told me what to do so I just do things."  I've had that experience myself throughout my entire career.

When people are put into the role of the application architect by default, they are often restricted from making an impact.  They are often bearing the load of unrealistic deadlines & static scope.  They *want to do better*, but they are not enabled to do so.

Are you in this situation now?

* Acknowledge that maybe you are the default, and leadership doesn't believe your ideas will bring results; **you may not really be what you think you are**.
* Learn to make an impact as you go on your journey, always

If the industry continues to suppress, [how will this be any different with LLMs](../practical/grim-trajectory.md)?  *Why* would they now invest in productivity over feature velocity?

## Product / Engineering friction & application architects

The struggle as an application architect will always be when they lack the autonomy to follow through on what they are accountable for.  In a world where every piece of work must be justified against KPIs relating to immeasurable outcomes, it can be challenging.  An application architect can scope out dozens of pieces of work that would improve feature velocity over time.  But if that work is [not prioritized over features](../practical/grim-trajectory.md), you can't hold them accountable.  Not enabling individuals to autonomously prioritize their own productivity is a **leadership decision**, which then steals the accountability and ownership of the health of the application codebase.  It puts that onus on management, who know very little about and have little influence on the codebase directly.

You can't empirically measure feature velocity.  

* It's not lines of code
* It's not number of pull requests
* It's **subjective**

Yes you can measure some things and also measure the change of those things, but strong architecture does not yield immediate boolean evaluations.  **It's far too complex**.

I have found success in owning my own productivity without asking for permission.  I update my IDE configuration when I need to.  I update my workflow when I want to.  I continuously improve and I deliver value.  Harness engineering requires more than that.  It requires a lot of thought and effort.  It requires dedication.  It needs to be the primary objective for those who understand it, not the secondary objective.

Start giving engineers a clear and unambiguous direction on their contributions towards future productivity vs feature development.  Track hours if needed.  Declare it as 100% of their time, 50%, 30%, 10%, or 0%.  If it is 0%, be intential and honest about it.

## Application architecture

The codebase should aim to be akin to a superconductive magnet for a high speed maglev train system. The term I love to use is they continuously identify and eliminate **friction**.

### Architecture & organized code (application architecture)

* Maintain useful and powerful abstractions that support application use cases
* Eliminate wrong abstractions, plug leaky abstractions, separate concerns
* Reorganize concepts and structures within the codebase to maximize how easy it is to extend the code and review changes
* Maximize testability and maintainability without sacrificing other runtime architectural concerns
* Improve pluggability to allow agents to interchange pieces to verify functionality
* Continually push observability to enable agents to understand local and deployed systems
* Provide and maintain exemplars in the codebase for agents to follow (or make all of the code equal in quality)
* Provide guidance and solutions to problems that the team of developers encounter when constructing larger new systems
* Create computational checks and inferential LLM prompts that autonomously eliminate hallucinated antipatterns

### Results

* Positive feedback loop experiments, such as [Forward deployed engineering](./forward-deployed-engineering.md) become more efficient
* Improvements to system health (reduced downtime, reduced degredations, reduced bugs)
* Improved token to feature spend ratio
* More optimized code review cycle (well structured code is easier for humans to trust and review)

Indirectly, application architecture pushes more features and more value, equating to more revenue.

## A natural fit for the harness engineer

The application architect has historically been the person who is responsible for a team being highly productive while they work.  They understand complex high level concepts that allow them to create elegant, simple solutions to complex problems.  That skill has historically resulted in projects that do very well over time.  Feature velocity doesn't go down, it goes up.  Dividends are gained from architectural investments.

Organization of code has always been valuable to humans.  It allows developers to work in areas and make changes without friction.  It allows developers to change things without breaking things.  It allows developers to isolate an area and understand it in its entirety, quickly, before making the changes to how it works.

LLMs benefit from all of this.

**Application architecture is an incredibly important aspect of harness engineering**.  It produces code that is easy to change, and LLMs thrive on codebases that are easy to change.

I believe that the harness engineering role is a natural fit for application architects, but a harness engineer need not be an application architect.
