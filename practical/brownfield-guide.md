# Brownfield guide

A practical set of actions to bring a brownfield project to a state where agents are productive.

## Adhere to the important tenets

The four primary tenets that I use within my Canon are:

* Observability
* Testability
* Discoverability
* Pluggability

All of the actions within this guide are anchored to those tenets.  These guide us on what improvements to make.

## Phase 1: Context

The first phase is to provide structured context to your agents.  This is the most basic step into [harness engineering](../concepts/harness-engineering.md) and agentic development.  An AGENTS.md file or CLAUDE.md file with some basic skills and information can bootstrap agents so that they spend less time reverse engineering in each conversation and more time working towards the goal.

* Create markdown files to support your repository
* Establish a [progressive disclosure](../concepts/progressive-disclosure.md) enabled encyclopedia of context for your agents

## Phase 2: Workflow

Each developer will begin to establish their new flow.  They'll create their own personal skills, souls, and preferences for how they work with agents.  Developers should embrace creativity.  Bring your own workflow.  Share your workflow and your workflow ideas with your team and organization.  This breeds innovation and creativity.  Don't try and create a core workflow for all developers to use.  Pushing conformance smothers innovation.

* Create a culture of sharing new ideas and agent workflows
* Build on each others work
* Establish an understanding of dependency inversion of [workflow and context](../concepts/application-harness-workflow-workspace.md) by building skills that work across any project

## Phase 3: E2E agent validation

Effectiveness of an agent is improved dramatically by the capability of said agent to run the full stack of an entire application and have insights into whether it is working or not.  This will be a large hurdle for a lot of organizations.  Strong application architecture may already exist to support this.  This is where an [application architect](../concepts/application-architect.md) can help the most as they should understand how to modify the application to support this new trait.

* Modularize and abstract concepts like M2M auth and native cloud services to be able to use their local counterpart
* Create mock application services for external dependencies that are pluggable and highly configurable
* Add context to inform agents how services work together
* Add context to inform agents how to read service I/O to [validate the software is working](../concepts/agent-verification.md) or discover errors
* Create test data management tooling to enable agents to quickly set up specific states

## Phase 4: Local ephemeral environments

Developers will start to be blocked by wall time.  A single agent will work longer and leave the developer waiting.  Naturally, a developer will begin to run a second agent in parallel.  The first agent works while the second agent is dialed into their task.  When the first agent completes, the developer can review the output while the second agent works.  Running two agents in parallel greatly reduces the amount of time they are waiting.  Extending this to three, four, or five can improve productivity further, but dual agents is significant enough on its own.

* Allow the application to be configured to run on any port or resource in their own isolated domain
* Enable tools or context to enable LLMs to quickly create or destroy environments
* Absorb more E2E flows by keeping everything local

Rich, local test data can become a large gap.  Enhancing test data management tooling starts to be appealing as agents would be able to setup complex scenarios for their own testing.

## Phase 5: Automate ops

Organizations with complex processes around merging and deploying changes will start to see their old pipelines become the bottleneck.  Developers should begin to curate their own skills to execute processes against their project's requirements.  Additionally, local environment operations may begin to feel cumbersome.

* Developers should seek to automate minutia like creating branches, merging, pushing code to a feature branch, and resetting environments
* Complex merge requests with gates (linting, integration tests) should be described in context, CLI tools enable agents to resolve any issues or errors
* Organizational documentation for change requests, change sets, release notes, etc can be created by LLMs
* Organizations can explore LLM guided deployments

## Phase 6: Domain Harness

Building up the context for the application begins to be more of a focus for the engineers.  The [domain harness](../concepts/harness-components.md) holds a critical mass of information that enables agents and is continually extended.  Optimization and correctness of the harness becomes a debated topic.  Extensions now need to be managed.  An initial set of context now becomes a project of its own.

* Context can be moved into its own repository (polyrepo) or area (monorepo) with its own evaluation criteria
* Changes are backed by evaluations - "Does this prompt yield better results with this change to the context?"
* Day to day now includes pruning, updating, and reviewing context changes
* Introduce the context reviewing agent that ensures context is complete and correct.

## Phase 7: Canon feedback cycle

Developers continue to use agents to build the application in their day to day.  While they do so, each failure can be a retrospective item to improve harness capabilities.  Patterns emerge as AI generated code is spotchecked.  The team begins to use the failures to improve the context.

* Establish a canon that governs the domain harness
* Introduce a harness review agent that sources data from a variety of places to generate retrospective items
* Developers process retrospective items, acting on them to engineer a more autonomous system

## Phase 8: Simplification of the application

As agents become more autonomous, the domain harness becomes richer, and processes are more automated, a different problem shows up.  Agent output reaches a plateau.  Attempts to improve the context have diminishing results and the agents just can't produce the _right_ output.  They struggle building within the application due to inconsistencies and a lack of organization.  LLMs pattern match against existing antipatterns producing code that humans don't have confidence in.  Changes in big ball of mud architecture can be more difficult to review by humans.

* Use agents to organize the code into a desired pattern
* Remove antipatterns that perpetuate
* Aggressively add end to end and integration tests to improve confidence
* Evaluate the choice of language (Python vs Rust) - agents may produce better code in Rust
* Optimize the process to maximize the output to review-effort ratio

## Phase 9+: Engage in harness engineering

All of the work spent to get this far should enable the application to be harnessed in the same way as any greenfield application.  The biggest difference between a greenfield and brownfield application from the perspective of harness engineering is the application architecture, its observability, testability, discoverability, and pluggability.  Investing in these tenets should provide noticeable efficiencies.

Other areas to explore on your journey:

* Utilizing agents in areas of the application unrelated to the code can be done at any time
* A harness can be comprised of sets of markdown files from different areas (organization wide standards vs project standards)
* Your git history is data an LLM can consume to understand human failures of the past
* Your code review history is data an LLM can consume to understand nuances, standards, and non-functional requirements
