# Local ephemeral environments for agents

Provide agents the ability to [close a loop](./agentic-development-testing-loop.md) on their own work by running the application in an exclusive feature environment.  Give the agents the tools to manage and work within their environments rather than placing them into a single environment we cooked up.

## Establishing confidence in agent work

One of the best ways to [establish confidence](./agent-verification.md) in software is to ask the questions...

* Does it work?
* Did you try it?
* What did you try?

Agents may be stuck with only unit tests and code evaluation to validate they have achieved their goal.  For a lot of software, this isn't enough.  A full end-to-end test, smoke test, or regression test adds confidence that all of the pieces are correctly assembled.  Automated tests are essential, but there are often nuances the tests miss.  Furthermore, the tests alone may not assert all conditions that are required for the application to work correctly.

Give your agents the capability to bring up the application as a whole and verify it on their own.  When you do this, you can ask your agent, "Does it work?" and the agent will tell you.  It'll tell you that it never tested it or it'll tell you that it executed a variety of test cases against the live, local environment that was set up.

For me, personally, connecting the agent to the application itself was one of the larger unlocks in improving long-running agent tasks.

## Multiple environments

In our journey through the [stages of agentic development](./walk-run-wheels-rocket-into-space.md), we will eventually hit a point where an agent is running on one task for long enough that we'll want to set up a second agent to work, side by side, on a different task.  This leads to the dual-agent mode where humans review one output while another output is being generated.  As of July 2026, there is a bit of a gap here in the tooling.  Parallelization of tasks through cloud-based environments is an interesting idea.  But doing this requires tackling a lot of large problems and when you get there you are now detached from the rich local environment.  You can't review locally with your own diff tools, you can't inspect things locally, you can't have that infinite observability.  I'm just not sold.

Maybe I am stubborn and holding on to the old ways.  Or maybe I feel like my productivity using horizontally scaled cloud-based environments doesn't match up to my productivity using horizontally scaled local environments.

Either way, it makes sense to me for agents to work in rich local ephemeral environments.

### Simple applications like CLIs

For simple cases like a CLI tool, the agent can build and run it locally.  If the tool lives in its own repository, it can utilize simple worktrees via native code-harness capabilities to run in an isolated area.  This basic use case is streamlined quite well.  This is an example of how an agent can exist in its own feature environment answering the questions above.

### Complex applications like SaaS platforms

Eventually an application will grow to more than just a simple concept (see the [Brownfield guide](../practical/brownfield-guide.md)).  It will start to have multiple web applications, services, databases, message brokers, and other systems.  It will have third-party integrations.  It becomes harder to set up a local environment.  It becomes harder to set up multiple systems that work in isolation.

* Workspace-level services like Postgres, LocalStack, or RabbitMQ need to be provisioned in a way that resembles multi-tenancy
* Application services must be both configurable and pluggable
* Rich datasets must be able to be injected
* Mock external services must be stood up and their responses may need to correlate to the local test data
* Something has to manage these processes, and the agent can't do it alone

## Service orchestration

The goal is to manage multiple instances of your application suite on your local machine.

* Local environments will likely require local resources
* Ports or port ranges need to be allocated to different environments
* Services must be built and run
* Dependencies must be installed
* Data / resources must be provisioned
* Lifecycle must be managed
* Input (web & APIs) and output (logs) should be accessible to humans and agents
* Internal services should be accessible too (direct connection to databases or message brokers)

### Environment / service lifecycle

The very first iteration of this process is to ask your agent to run the service in the background while it executes a browser-based or curl-based set of tests.  This will get a foot in the door.  The first issue we face is that the background process is orphaned.  Agents can start, but they're not great at stopping.  At any point, the human steering the operation can stop executing commands.  If no turn is executed then no cleanup can occur.

* Named tmux sessions can be a great way to hold the process tree, giving both humans and agents insight and control
* Docker / Docker Compose can be utilized as well
* Kubernetes can be another alternative, though it might be heavier than what a local environment needs for most users

What an agent needs isn't instructions on how to manage tmux sessions, *it needs an abstraction*.  Give the agents the tools needed to manage **feature environments** and **multi-repository feature environment worktrees**, **spin up and tear down services**, and **provision resources and data**.  The agent doesn't need to know the details, it just needs the basic tool to complete its own task.

## One agent, many environments

Let us let go of our assumption that one agent should have one environment.  A single agent interface with modern models like Opus 4.8 or Fable 5 is very capable of managing large workloads across many environments, utilizing subagents as needed.  Claude Code's [dynamic workflows](https://code.claude.com/docs/en/workflows) show this off quite well.

Give your agent a dozen tasks and tell them to implement them across four local ephemeral environments.  They will detect opportunities to work in parallel or identify areas where work must be done sequentially.  They will manage the queue of work and distribute it to environments as they open up.

Orchestration of tasks does not need to be a web application with a kanban board with a proxy terminal.  We can choose to embrace the AI-native approach of rich read-only views with agentic modifications.

## Why local

We are not yet at a point where agents will consistently produce the desired outcome without any human iteration.  If features that are built need to be reviewed in some capacity, async cloud-based processes expand the feedback loop.  As we approach the human-on-the-loop agentic flywheel, a human having some insights into what is going on is still appropriate.  High-level architectural decisions and steering may be best done in a more interactive manner.  With models like Fable 5, having architectural discussions as part of the building process may be a trending new pattern.

Cloud-based agents will benefit from a rich local ephemeral environment just as much as a locally run agent.  There is synergy here.  Make it work well for both and get the best of both worlds.  Let the cloud agents handle the more basic tasks that they can do reliably.  Let the humans run the more complex tasks locally.

### Conversation / iteration on the task

Even with a well harnessed application and a reliable agentic development flow, we may find ourselves interacting with the agent on almost every task.  As soon as it completes, we ask questions like, "Why did you do this?" or "Tell me about an alternative way of doing this."  Additional insights into how the agent performed can be used to tweak the harness workflows and autonomous behavior.  If we move our workflow to be asynchronous, it is a lot harder to have that conversational flow.  It's harder to manage the context.  We lose out on vital cost-reducing caches for long-context conversations.  We add more latency to each turn.  We add complexity where comments on PRs trigger webhooks that spin up cloud environments and restore conversations just to do a single turn and then shut it all down.

In some capacity, an interactive terminal will remain.

### We're not at the bottleneck where cloud agents are needed

As far as I know, very few people (if anyone) are at the point where they are slinging so many tasks at an agent that they can't do it locally.  We don't need to offload our work to a cloud agent yet.  Even if we are at that bottleneck, we would have to have chunks of work that can be worked on in parallel.  You can't put sixty agents on one small feature.  It's the same problem we've faced with human developers manually writing code for the past half-decade.

Even trivial bugs don't require a cloud agent.  A ticket can be created from the bug by any means.  A developer can point their local agent at an array of bugs and tell it to fix all of them in a local feature environment (or an array of environments).  The time investment comes from reviewing, merging, deploying, and verifying the change.  This can be especially true in brownfield applications with complex release processes.

We can open another terminal tab, provision another feature environment, and send another agent to work.  Locally, we can have a dozen agents working just fine.  If we run out of system resources to support running a dozen applications at once, we can set up a second machine with a KVM switch for the keyboard & mouse.  I have certainly felt the need to have more memory from time to time, but it hasn't been a blocker.  Even if we have a dozen agents working in a dozen feature environments, they may not all need to have the services up and running at the same time.  They can provision as needed, tear down when completed, and optimize system resources quite well.

## Winter

This concept and these problems are why [Winter](https://github.com/paul-gross/winter) was created.  It aimed to create an agentic interface to a multi-agent, multi-environment local machine.  It was created in the winter season of 2025-2026 (hence the name).  It has been iterated on since then to solve problems that were encountered developing against large brownfield applications.
