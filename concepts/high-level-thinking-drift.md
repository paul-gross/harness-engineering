# High level thinking drift

The act of giving an agent an extremely high level prompt will always produce a wildly drifted output

## What?

Suppose we told an agent to *Create an agentic harness for my application*.

It'll start with a plan.  It'll research the codebase and form something.  That plan will be *a file*.  We've gone from a sentence to a file.

If you look closely at the file, you'll notice there are *things* in it, but they aren't really useful.  They are small bits of drift or hallucinations.  Maybe it misunderstood a concept.  Maybe it embellished it with an idea. You now have two options.

* Embrace [Lift](./lift.md), send it
* Iterate on the plan, slice it up into pieces and make it exactly what you want

Now that one file *becomes a commit*.  It's hundreds or thousands of lines of code & markdown.

If you look closely at the output, you'll notice there are *things* in it, but they *aren't really useful*.  If you embraced lift, you now have 2 levels of drift applied to the outcome.  If you iterated on the plan, you only have one level of drift applied. Drift applied onto drift (two levels) washes out the original idea.  Try it and see how it does.

Now that you have your agentic harness, you start to feed it features.  That one commit *becomes dozens or hundreds of commits*.  If you embraced lift, this is the third layer of drift.

### High level thinking & recursive drift

The above should give you a basic understanding of how a small prompt with high expectations can often go off the rails.  I've tried to use AI to create *things* that AI uses to create *more things* and it was a struggle.  Eventually I opened a conversation with Opus about it and it was actually great at explaining what was going on.  Drift.  The imperfections and hallucinations build up over iterations of AI refinement.  This is why [AI cannot harness engineer](/philosophy/ai-cannot-harness-engineer.md).  The more high level instructions we give it, without steering, the more *grey* it becomes.

Grey isn't even a great term for it.  I can't describe it any other way than *Drift*.  It's a great term.

Going more high level with an LLM isn't always the answer.  Instead, try going more *horizontal*.  Don't give it an concept and expect to get 20 systems out of it.  Give it 20 concepts to get 20 systems out of it *and steer it*

### AI Generated markdown files & drift

It is easy to fall into the trap of using the LLM to generate the context that feeds back into the LLM.  It's quick and it seems to have quick wins.  But [LLM Generated markdown files actually hurt performance](https://arxiv.org/abs/2602.11988).

* Use LLMs to stub out *something* that gives you a starting point for a conversation with an LLM
* Iterate on the markdown files both strategically (how to divide and slice context) and tactically (how the context is written)
* Iterate on your *skill* skill to get it to stub out something that requires less iteration
* Eval it if you can -- have your LLM spawn 100 agents that all give the same basic task or question, ask how many responded correctly (It's really that simple).
