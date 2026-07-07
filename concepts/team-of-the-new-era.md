# Team of the new era

Understanding the dynamics and shape of a modern engineering team.

## Less is more

The concept of less-is-more in the software industry is not new (see the classic lichess vs chess dot com example).  Many software engineers have understood for a long time that simply adding more people to a project does not equate to improved feature velocity.  We see increased overhead, more conflicts, lack of ownership and accountability, planning headaches, and other issues.  Too much elbow bumping.

There is tipping point where adding more developers will decrease the absolute feature velocity.  I'm not referring to decreasing the cost per feature, I'm referring to a decrease in total velocity.

Typically, each developer beyond the first can decrease the cost per feature.  A single developer project seems to be the highest feature cost efficiency, but also the lowest for absolute feature delivery.

[Laskowski & Michalak](https://handsonarchitects.com/blog/2026/the-harness-model-ai-engineering-maturity-matrix/) indicate that team shape changes with harnessing from large specialist to small generalist per initiative to generalist across multiple initiatives.

## Giving space

* **Developers need room to work**: They need space to build without worrying about changes that may occur in the system outside of their focus
* **Developers work better with ownership**: Focusing in on an area helps developers iterate more effectively vs touching many systems briefly
* **Developers need autonomy**: The people who know best how to solve the problems within an application are those who are actively in that application space

Different aspects of an application can be distributed to different engineers as the application grows.  The traditional separation has often been quite simple.

* **DevOps**: A great candidate for iteration by a specialized engineer being added to the team
* **Frontend vs Backend**: The classic and most common bisection in software engineering skillsets
* **Integration**: Connecting applications to the outside world
* **Domains**: Business areas of the application that have more isolated areas

With harness engineering entering the scene, our understanding of space changes only in the volume of space needed.

* **DevOps**: A single engineer can now manage DevOps and infrastructure across more projects
* **Frontend vs Backend**: A single engineer can now more easily work full-stack end-to-end with LLMs
* **Integration**: A single engineer can now own integrations across a suite of applications and services
* **Domains**: A single engineer can now parallelize work across multiple domains using multiple agents

An LLM doesn't help a frontend engineer understand Kubernetes, nor does it help a backend engineer understand how other applications work.  The distribution is human centric, with LLMs being a force multiplier.

What could be achieved with a team of 7 in the past can now be achieved by some individuals alone, assuming the application has a harness that is well-maintained.  Such an individual would need to be exceptionally talented and well rounded in many areas.  In practice, a small team of 2 or 3 engineers with support from cross-application specialists would be a more realistic target to aim for.

## Specialization, autonomy, and ownership at the core

I've always believed that autonomy, specialization, and ownership have had the biggest and most impactful benefits to an engineering organization.  Strong leadership governs what matters at high levels to manage macro level complexity and less impactful architectural decisions are left to junior, mid level, and senior software engineers.  At every level, specialization, autonomy, and ownership provide more results.  The level of talent and skill determines whether those results are positive (talent in the right place) or negative (peter principle).

The new roles seem to be moving towards:

### An [FDE (Forward deployed engineer)](./forward-deployed-engineering.md)

* Attentive to client or user needs and concerns
* Exceptionally knowledgeable about patterns in applications (not the code, the user's perspective)
* Problem solving through creative thinking -- creating elegant ideas that help users solve their complex problems

The engineers who lean into the product mindset will gravitate towards forward deployed engineering.  They are the ones who can be given ambiguity and produce something of value.  They embrace agentic development but have little interest in building the harness itself.  They solve the user's problems in real time.

* They focus on feature development and iteration on existing features

### The future software engineer

* Understands and learns system design concepts quickly
* Strong knowledge of tools, frameworks, and software development concepts
* Comprehends complex systems and abstractions and works well within them

The engineers who lean into agentic development, the core of the modern software engineering team

* They build features
* They build infrastructure to support the application
* They maintain the system's invariants, health, and important architectural traits

### The [Application architect](./application-architect.md)

* More capable of abstract thinking - an abstractionist
* Tends to have more high order thinking
* Clear vision of big picture / future state

The engineers who break down concepts, categorize them, and simplify them.  Application architects improve complex solutions to simple problems and derive simple solutions for complex problems.

* They manage macro level complexity, resolving tech debt
* Work with harness engineer to improve feedforward and feedback mechanisms in the harness
* Make general improvements according to the tenets of the project, becoming a force multiplier for the team

### The [Harness engineer](./harness-engineer.md)

* Thinks in the meta - thinking outside of the box, solving problems using derivatives
* Process orientated
* Solution Architecture

The engineers who obsess over developer experience and feature velocity.  They see LLMs as a tool and respect that it takes them 80% of the way.  When it comes to the last 20%, they default to making adjustments to take it to 90, 95, or 100% over taking it to the finish line by hand.

* Improve the harness, automating more and more aspects of the software development process as the applications mature and age
* Connect developers, through the harness, to disparate systems via MCPs or CLIs for workflow improvements
* Manage overarching systems that enable LLMs to oversee the deployed production application
* They build features to evaluate the harness

## Breaking down roles and responsibilities

Classic software development teams may have been created as a bag of people left to self organize.  This will always work but it may not be optimally efficient.  Typically we've seen team leads, tech leads, architects, and career rank added to the mix.  That's okay too, it works.  Or at the very least, it results in an application *eventually* being built.  After being a part of countless self organizing teams, I feel I have a good sense for what has helped things move forward and can extrapolate what will come in 2026 and beyond

For lack of a better term, vibe coding can simply be the act of building software and embracing [Lift](./lift.md).  Vibe coding should not be dismissed, it should be understood, acknowledged, and respected.

* The forward deployed engineer should have some autonomy and be allowed to vibe code and push code that violates the architectural invariants of the codebase
* The forward deployed engineer is the spearhead of innovation, primarily building within client scoped feature flags
* The harness engineer & architect should have generous amounts of autonomy to give ample space
* The application architect is allowed to set & change the rules and invariants of the codebase
* The application architect continuously monitors the invariants and refactors based on their judgement (or if the harness engineer can supply data, that is better)
* The software engineers are focused on building features and infrastructure to support the system

The technology organizations of the future will heavily rely on the expertise of the harness engineers.  It behooves leadership to give respect to this new role.  Find them and listen to them.  We should understand what they can do and the value it provides.
