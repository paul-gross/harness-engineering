# Exemplars

*This is how we do things around here.*

## What?

Change takes time.  With a change in how we work, we inevitably leave the codebase in a state where something is done in many ways.  This way, or that way, depending on where you look.  An LLM will adopt the pattern it sees based on where it is working and what it has read.  If it is working in an untyped javascript project, it will produce untyped javascript.  If it is working in a Typescript project with strong, strict types in place, it will produce Typescript code with strong, strict types.

In short: An exemplar is a deliberately ultra maintained part of the code base that is exactly the way it should be done.

* If you want to have summary comments, it should have summary tags
* If you want to have unit tests, it should have unit tests
* If you want to use clean architecture, it should use clean architecture
* If you want Services to be called Bumblebees, **it should be a BusinessFeatureBumblebee class**

Point humans and LLMs at your exemplars to steer new development to the desired style and approach.  LLMs are much better at positive examples (DO this) than they are at negative examples (DONT do this)

## Comet tail of change

Software is rarely purely consistent.  In a perfect world, an incredibly strong [Application Architect](./application-architect.md) is involved from the very beginning, and everything is *done right*.  In reality, projects are started as a proof of concept, they are *rushed*, and the engineers make mistakes as part of their career development (we all make mistakes, this is how we learn).  The scrappy startup project eventually struggles due to [tech debt](../application-architecture/tech-debt.md) or excessive [lift](./lift.md).  Talent is brought in to *make things better*.  They can't change everything overnight; they change things over time, leaving a tail of old patterns and concepts to die in closets and under floorboards.

* The strangler pattern is the defacto strategy for change, and should always begin with an Exemplar
* Over time, the new pattern is adopted

## Exemplars are hard

Acknowledge that setting the vision and goal is hard.  It's not easy.  It requires a lot of understanding.  No matter how much you think you know about what is best, **it'll probably change** and that is okay.  Keep in mind, [you are the exemplar](../philosophy/we-are-the-exemplars.md).  Steer the LLMs to act like you, to do as you would do, and trust that it is right.
