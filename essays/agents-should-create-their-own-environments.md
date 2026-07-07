# Agents should create their own environments

I used to ask my agent, "Does it work?"

It's not unlike something an engineering manager would ask the senior developer who is reporting in about a new feature that they just finished.  The answer may be, "The unit tests pass."

I'd often have to tell my agent, "It doesn't work, and here is why."  My agent kept building code that didn't work.  It'd compile, it'd pass its own unit tests and linting rules, but when I navigated to the web app, the new button did nothing.  It was missing something.  I was missing the [end-to-end verification loop](../concepts/agentic-development-testing-loop.md).  I opened a few tabs in my terminal, launched a few services and database migrations and then told the agent to open up a browser to make sure the changes worked.  The browser route went alright, but it was a bit slow.  After that I started having it interact with the APIs and run the CLIs.

Now my agents run the code with the changes in real environments exercising full end-to-end flows.  They create the data they need to assert the edge cases they consider.  They run longer and produce better results.  

Naturally I open a second, third, fourth, or fifth tab. I spin up some more agents.

## System Isolation

When we make a worktree, we're making an isolated area for the code, but we're not isolating the runtime.  The coding harnesses have native worktree capabilities.  This gives them a place to make changes and run tests effectively.  It doesn't give them a space to run those services.  Two worktrees try to launch the API at the same time, one fails due to a port conflict.

This is the problem.  We're not talking about service orchestration and [local ephemeral feature environments](../concepts/local-ephemeral-environments-for-agents.md).

The bet on worktrees paid off.  For applications that require no resources, we're seeing success.  What about complex applications in the [brownfield](../practical/brownfield-guide.md) space?

We can give each worktree a custom .env file, curated by an agent.  It uses a complex prose-based markdown file to lay out what ports to give to each environment.  That's a bit brittle, slow, and token heavy.  I went down that route.  I liked the taste of it, but I wanted more than just a taste.  I wanted a solution.

We tell the agents to spin up the services.  It's a lot of instructions laid out in various markdown files or READMEs that eventually lead to new problems.  Agents leave orphaned processes behind that don't get spun down.  We don't know what is working or what isn't working.  We can't see if there is a build error, it's all hidden behind the agent.  Sometimes the agents just execute the wrong command.

I was in a remote job interview earlier this year and everything was choppy.  My CPU was destroyed.  It turned out I had a dozen instances of my personal project's API running in the background.  All orphaned instances from Claude Code agents left behind.  That's something I'll always remember.

To solve this problem, we can look to the cloud.  Create a completely isolated environment for our agent to run.  We give up the efficiencies of local development for horizontal scaling.  Each cloud environment gets its own sandbox so it won't clash with any other environments.  But we lose all of our local tooling.  Everything has to be thought up from ground zero.  We now begin the era of Kanban-style agent orchestration user interfaces with proxy terminals.

Let's talk about another way.  Instead of putting our agent in the environment, let's give our agents the capability to orchestrate their own services in their own environments all by themselves.  Move from one agent : one environment towards one agent : *many environments*.  Instead of giving them a complex set of instructions about managing tmux sessions, docker containers, or kubernetes clusters -- let's give them *an abstraction.*  Have them start the services, stop the services, check the logs, provision the resources, and seed the data, without the specifics on how that is done.  I refer to this as *agent-managed environments*.

Now my workflow is often to task my agent with a half dozen or so GitHub issues.  I tell it, "Work on the following ten issues, use three feature environments, use the workflow skill that handles task management / distribution to Sonnet-class subagents."  They resolve the issues, execute pre-release checks, and fold the code review fixes right into the corresponding issue's commits.

## Agent-managed environments

I use a workspace for this.  I call it [Winter](https://github.com/paul-gross/winter).  My workspace is built for agentic development.  It helps me create feature environments that support polyrepo worktrees, provision resources, and manage services.  It grants the tools to the agent so they can do it themselves.

<video src="../assets/agents-should-create-their-own-environments-demo.mp4" controls muted playsinline></video>

* I tell my agents to spin up the services on the respective feature environment, they run a deterministic CLI tool that manages the services
* I tell my agents to check the logs of the services and look for errors, they use the CLI tool to aggregate all of the backing service logs into one stream to look for errors
* I tell my agents to reset my environment, the CLI tool runs the commands to tear down, spin up, and seed the resources

The agents use the simplified abstractions.  The details are left to the tool.  I use a combination of static environments (alpha, beta, gamma) and dynamic feature environments (feature-xyz): `winter service alpha up`.  Each environment gets a block of ports, each service gets a port within that block.  Port ranges are secured when environments are created.  Workspace level services like postgres can operate in a docker container in the workspace port range.  Feature environment level services live within tmux sessions.  Winter brings it together: `winter logs beta --since=60s` = one basic command for all relevant logs.

The agents can check the status, see the logs, and restart individual services as changes are made.  Output can either be structured JSON for agents or docker-esque charts and tables for humans.  

When the agent finishes the task and I check it out, I might see an endpoint throw an error.  "Getting an error in my browser when I try this feature edge case, check the logs." And the agent checks the logs, figures it out, and fixes the issue.

## The unlock

Feature environments buy us horizontal scaling and movement towards more human-on-the-loop tactics.  An agent with a [self-verification loop](../concepts/agent-verification.md) can demonstrate more evidence to support that the goal has been achieved.  They can detect issues they wouldn't have caught if they were coding blind.  Real integration issues happen in the seams between highly tested and cohesive components.  Feature environments help agents find them before you even start reviewing their output.

Where does this go?

* Best of N attempts: Have three agents work on the same task in separate feature environments, keep the best one
* Local experiments & harness science: Run many smaller tasks horizontally with your own [harness](../concepts/harness-engineering.md), each with a different tweak to the prompt, compare the output to understand how adjusting the harness affects the output.
* Destructive testing: Enable the agents to tear down services and test unstable application states as part of their definition of done
* Mock services: [Agent managed tooling](../concepts/agent-managed-tooling.md) with knobs and levers to simulate external service stability, instability, edge cases, latency, or rate limiting

I no longer ask my agents, "Does it work?"  They now explain what they verified in their closing summary before I get a chance to ask.
