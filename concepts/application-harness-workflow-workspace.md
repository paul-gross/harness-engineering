# Application, harness, workflow, & workspace

Agent native development has shifted the way developers work by injecting new ideas into daily tooling that don't fit the traditional mold.  Where does the harness go?  What is in the harness?  How do I manage the harness?

Where [harness components](./harness-components.md) decomposes the harnessed application into its parts, this note zooms out a level to place the application, harness, workflow, and workspace relative to one another.

## Making the case: the harness belongs in its own area

When we first step into harness engineering, Claude Code guides us to create a CLAUDE.md file that contains everything the agent needs to know to work on the repository.  This is a misleading start.  It puts us on a path that our application should be intertwined with the context that helps agents understand it.  The paved path is to put CLAUDE.md files in each project directory.  The downside is that these CLAUDE.md files defy [progressive disclosure](./progressive-disclosure.md) by forcing agents to read files that provide information that they may not be interested in.

When we are working with polyrepo applications, the choice is clear.  A cross cutting harness cannot exist within a single repository.  Instead, we glue an additional cross cutting harness repository adjacent.

Monorepo applications can embed the harness inside of it like any other project.

As we progress along the harness engineering journey, we will continually treat the *harness* as the application, applying aged software development principles to the harness just as we have with an application.  The code becomes ephemeral and unimportant.  To pair the harness with the code is to plan for a future where a harness's code is pared directly to it.

## Harness and workflow

Determining what goes into the markdown files and why can be contentious.  Large teams may have disagreements over the way things are written.  The structure of the harness may not align with the individual developer's workflow.  Maybe some developers like to use docker compose to bring up services, but others like to run them locally.  Maybe some developers like to have their agents write tests before code and others prefer tests after code.  Maybe some developers don't need to use all 30 MCPs and don't want the context of their agents to be polluted.

**Leave the opinionated stuff out of the harness**, let each developer bring their own workflow.

Separation of harness and workflow ensures that the only thing in the harness are the objective facts.

* **Project overview**: Information about relevant repositories and their function
* **Project setup**: Instructions guiding agents on how to scaffold the application locally
* **Application architecture & architectural governance**: What code goes in which project, owned by the [application architect](./application-architect.md)
* **Code conventions**: Patterns & standards the teams have agreed upon
* **Service topology**: Holistic big picture for agent planning
* **Interchangeable mocks & configuration**: [Agent managed tools](./agent-managed-tooling.md) supporting local ephemeral environments
* **Domain model documentation**: The source of truth of the business rules
* **Feature development expectations**: Agent's definition of done
* **CI/CD pipeline information**: Inform agents how to interact with deployment mechanisms
* **Process documentation expectations**: Inform agents on how to write PRs, change requests, or design documents

What's left in the workflow?

* **Local ephemeral environment preferences**: docker or tmux sessions?
* **Personally flavored skills**:  code review, agent swarming, agent loops, [verification](./agent-verification.md) capabilities
* **Evaluation frameworks**: flows that evaluate changes to the harness itself
* **Agent definitions**: The preferred brand of tools each developer brings

The harness becomes universal and consumable by any role.  The workflows start to emerge as the [different personas](./team-of-the-new-era.md) begin executing on the application.  

* We will see non-technical stakeholders who may wish to ask questions about the application or make subtle changes
* We will see product and business roles contributing with basic workflows
* [Forward deployed engineers](./forward-deployed-engineering.md) will push tactical proof of concepts to users
* [Harness engineers](./harness-engineer.md) will adjust the systemic properties and flows
* Autonomous agents will diagnose and resolve issues, deploy software, or validate pull requests

All of these personas may bring a different workflow to the same harness.

## Workspace

Developers have always implicitly had a workspace.  There hasn't been much to it in the past.  With our increased productivity, plug & play workflows and harnesses, we begin to see a new way for managing the work we are doing.  We need a more generic solution to the problems that are faced as we segue to local agent based development.

These questions begin to unfold:

* How do we manage worktrees, especially in polyrepo applications?
* How do we manage local ephemeral environments, conflicting ports, isolated resources?
* How do we manage service orchestration, spinning up and tearing down end to end local ephemeral applications?
* How do we track work in progress across many local feature branches that may have active agents?
* How do we enable native code harness skills, rules, or MCPs for a given project?
* How do we split the seam of harness, application, and workflow?

These are all questions that are faced on this journey.  These are questions answered by a workspace framework like [winter](https://www.github.com/paul-gross/winter).
