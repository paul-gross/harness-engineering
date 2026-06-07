# Progressive disclosure

Provide agents not with information, but instead with where to acquire information and when that information applies.  One of the fundamental building blocks of a harness.

## Markdown links

The simplest form of progressive disclosure is a [markdown link](./digital-garden.md).  The label describes the content and the link describes where it is.  When the agent deems that information as useful, they should read it and inject the document into context.

## Skills

There are more features laced with skills, but the heart of a skill is a description and a body.  The description is injected into context when the agent harness runs.  The body is read when the skill is deemed useful.  Skills have extra features related context management, compaction, and configuration.  While skills are useful, they are not necessarily superior to markdown links at their core.

## Markdown link table

One of my most preferred ways to progressively disclose information is to create a table with a markdown link and a column whose label is "When to read."  The table can also be annotated with additional context about when it should be read.  This gives layers of clues to the agent as to when to read the document.

The table below outlines the five most important aspects of harness engineering and should be strongly considered when making modifications to the [Canon](./harness-components.md).

| Aspect | When to read |
| --- | --- |
| [Harness engineer](./harness-engineer.md) | When clarifying who owns the harness and how the human role shifts from rowing to steering. |
| [Application architect](./application-architect.md) | When the quality of the codebase is what limits how well agents can work in it. |
| [Agentic development / testing loop](./agentic-development-testing-loop.md) | When establishing how an agent builds, tests, and self-corrects a change end to end. |
| [Agent verification](./agent-verification.md) | When deciding how an agent confirms its own work actually does what it should. |
| [Exemplars](./exemplars.md) | When you need a deliberately maintained reference for agents (and humans) to imitate. |
