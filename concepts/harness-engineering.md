# Harness Engineering

The high level index about the hot topic of 2026: **Harness Engineering**.

## Introduction

Getting an agent to write some code is trivial.  Anyone can do it.  Getting an agent to write the right code in a complex application is difficult.  This is one of the main focal points of harness engineering.  Everyone has the same question: "How do we get the agents to write code effectively in our system?" Ask yourself a different question, "How do we get humans to write code effectively in our system?" and not end up on the [grim trajectory](./grim-trajectory.md).  Harness engineering shifts work done by humans to agents, evolving the human role into steering rather than *rowing*.

### Everything we read or hear about is greenfield

There is a large disconnect in what Harness Engineering is according to the most recent (as of spring of 2026) blog posts and podcasts and what it looks like in the real enterprise application space.  A few things to keep in mind.

* The applications that are examples for harness engineering are built from the ground up with harness engineering
* The applications are mostly *internal*, leading us to believe there is a more tolerable SLA, acceptance of downtime and bugs
* The applications don't seem to be parts of a legacy system

Keep this in mind as we explore how context engineering works in a *brownfield* environment.  The current narrative is around an idyllic environment.

### Breaking it down into parts

[The Harness Model](https://handsonarchitects.com/blog/2026/the-harness-model-ai-engineering-maturity-matrix/) did a fantastic job breaking down the harness into multiple dimensions.  It does a much better job than I will do, so I will simply list the dimensions here as reference

#### Foundation

* Context Engineering
* Team (Humans + Agents)

#### Governance

* Security & Trust
* Architectural Governance

#### Delivery

* Human-Agent Interaction
* Workflow & Process
* Reliability & Operations

#### Outcomes & Learning

* Verification & Quality
* Knowledge & Feedback Loops
* Planning & Decision-Making

### Breaking it down into components

The ten dimensions of the harness model is a great assessment of capabilities, but the implementation breaks down into [distinct components](./harness-components.md).  Those components work to establish the capabilities listed above.

* Application
* Agent Harness
* Domain Harness
* Canon
* Theory of harness engineering

### Workspace & Workflow

The workspace is an area that brings everything together.  It can be a git repository that is cloned down that straps the user into the harness.  Within the workspace, users are equipped with LLMs that have the capability to achieve various goals.  The harness equips the user.

The workflow is what the user's bring to the harness to do their work.  Each user has a different agenda, a different style, a different approach to how they want to interact with the harness.  They may like to use a GUI.  They may like to use a terminal.  They may like to speak conversationally.  They may like to have their own flavor of how the system is bootstrapped and brought up in their local environment.

The workspace is the platform where all things sit, the workflow is the processes that run within a workspace, utilizing a harness, to do work.

### In practice

Most simply: Humans identify areas where agents could provide additional value and implement a change that utilizes agents for that task

* **Humans**: Steering, guiding, context engineering, prompt engineering, system design
* **Planning**: Taking an idea and refining it to be an input to the agent

This is where the handoff occurs to the agent.  The human is no longer in the loop.  Depending on how far you are into your agentic development journey, the task is handed back to you after any one of the steps below.

* **Development**: Writing code
* **Evaluation**: Does it violate our invariants?
* **Verification**: Is it correct?

* **Review**: Human sign off
* **Retrospective**: What worked?  How can the harness be improved?

## Development, Evaluation, & Testing

Getting an agent to write some code is trivial.  Anyone can do it.  Getting an agent to write the right code in a complex application is difficult.  This is one of the main focal points of harness engineering.  Everyone has the same question: "How do we get the agents to write code effectively in our system?" Ask yourself another question, "How do we get humans to write code effectively in our system?" but without the [grim trajectory](./grim-trajectory.md).  There are a lot of new ideas to explore with LLMs handling more and more, but the fundamentals are still the same as the way humans work.

**LLMs and Humans are extremely similar**

What makes humans more effective is very likely going to overlap with what makes LLMs more effective, you can't go wrong if you optimize for human efficiency (DX).  But we can do better.

### Before development: guides, context, markdown, knowledge graphs

#### Research

The agentic tool of choice will research the topic and gather additional context based on the task.  

* The plan itself may include relevant topics (this can be done if you elect to do so as part of your planning process)
* The CLAUDE.md or AGENTS.md file will be the primary entrypoint into the repository
* Based on the task, the agent may load additional files that it is aware of, typically via markdown links

##### [Documentation optimized for skimmability](./readability-equals-skimmability.md)

Agents are nearly identical to humans who start a project on their first day, they can't learn your entire system and you don't want them to reverse engineer the entire thing, so you must have documentation designed to provide all of the answers without putting too much in their context

##### Domain documentation

If your plan is to create a video conference solution integration with a meeting invite, it is beneficial for the agent to understand how the meeting invite fits in with the application.  Is it part of a calendar?  Or is it part of an automated process pipeline?

##### Principles to follow

Help guide the way the code is written.  Should the code be OOP or functional?  Should it follow SOLID principles or is it more tactical?  Should it abstract things out?  Should it build features completely or follow YAGNI?

#### Reverse Engineering

* **Fundamental software / application principles**: Weak application architecture is harder to understand and change -- more context and thinking is needed per task

#### Execution

* **Instructions / Checklists**: Common scenarios can be executed by agents -- Agents are exceptionally good at step by step instructions (creating worktrees, pull requests, and so on)

### During development: sensors, evaluation, building, testing, validating

* **Compilation errors**: immediate feedback to the agent that can be fixed
* **Linting errors**: immediate feedback to the agent that can be fixed
* **Architectural assessments**: Subjective LLM driven assessments of the changes

### Verification: playwright testing, api testing, acceptance testing

* **Playwright MCP / Browser Testing**: More subjective LLM driven assessment of acceptance criteria
* **CURL / Command Line Testing**: Less subjective LLM driven assessment of acceptance criteria
* **Automated E2E Testing**: Even less subjective LLM driven assessment of acceptance criteria
