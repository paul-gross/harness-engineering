# Tech debt

That which supports something else with inherent flaws that, when corrected, warrant rewriting that something else.

## Misunderstood

Everything tends to get thrown into a bucket and labeled tech debt.  Much like architecture, it is an [overloaded term](../concepts/overloaded-terms.md).  This can make things challenging for the software engineer as tech debt may have a dedicated budget.  It is especially challenging when product focused features are masqueraded as tech debt.

Ask yourself what tech debt *really is*.

* Is it **being 6 versions out of support** on what version of node is used?
* Is it **inconsistencies in the UI**?
* Is it **feature related bugs**?
* Is it **a lack of architectural boundaries between application and domain concepts**?
* Is it **scaling challenges due to a growing userbase**?
* Is it **highly coupled interconnected services stuck in lock-step deployments**?
* Is it **a lack of an agentic harness in place**?

Those are all different things.  But they're probably all pushed into the tech debt bucket.  

If tech debt is simply defined as anti-productivity unrelated to features, then I would argue that a lack of an agentic harness *is* tech debt (at this point).

## It's not debt until you build on top of it

I've held the belief for a long time that tech debt isn't really tech debt until you build on top of something that is flawed.  No matter how big or small the flaw is, if fixing it does not require anything else to change other than the flaw itself, I don't think it qualifies to be in the same bucket.

So what is tech debt really, if you have to build on top of it?

You used an incremental integer ID and have public facing APIs that your clients depend on.  For compliance reasons (or public relations), you need to change your identifiers.

* You build something that is now flawed
* All of the external systems that rely on relationships to your data must now be changed to work with the new identifier should you migrate to a new identifier
* The tech debt must be paid in order to remove the incremental integer identifier

This is a simple example.  Another example of something that isn't really tech debt

* You build a function within a class that uses a complex algorithm to manage a heap based priority queue
* You use the algorithm to determine how to reprioritize items in a list
* The algorithm is 1500 lines of code in one giant function

That function exists in one class.  Nothing depends on it.  It's **dirty**, but it's not debt.  If you want to fix it, you do not have to change anything else outside of that class.  You could argue that you must repay the debt to have maintainability.  Or you could argue that 1400 of the 1500 lines of code depend on the 100 lines of code you need to modify, so those have to change too.  I won't debate it, I'm merely attempting to illustrate that some things are not tech debt, but rather a piece of code that hasn't been iterated on in the process of *make it work, make it right, make it fast*.

## Inherent & inferred dependencies

Immediately after you build a web application, your *user experience* depends on it.  While it is true that no code is building on top of your HTML, SCSS, or Tailwind -- something definitely is.  The user experience is about consistency, usability, accessibility, intuitiveness.  All of those factors depend on your application.

So while it is true that we don't incur debt until we build on top of something that is inherently flawed, there are some cases where inherent & inferred dependencies create immediate technical debt. Copying and pasting frontend component concepts throughout the codebase creates immediate technical debt -- you must deal with the sprawling code duplication to maintain consistency.

## Dirty code is okay

In the [tree analogy](./tree-analogy.md), features that rely on more core foundational parts of the application are easier to change.  The leaves of the tree can be dirty.  The code isn't reused, the concepts are distinct, and there is little need for abstraction.  Let [FDEs](../concepts/forward-deployed-engineering.md) push dirty leaves.

It's okay.

It's easy to change, therefore it's easy to fix and refactor to make it better.

Just don't build on top of those leaves, *push the functionality up into the branch, or the core, or the trunk*.

**Balance** the tree.

## Tackling tech debt

This really does deserve its own section. Tackling tech debt in the age of LLMs is wildly different than it has ever been before.  LLMs do exceptionally well at contained problems where there are existing specifications.  Rewriting a browser or C++ compiler is inherently easy, which is why those were chosen as the large projects for harness engineering to begin with.  Taking ambiguous high level product requirements that have no technical specification and making an application is harder.  Rewriting an API in another language.

Technical debt is often changing only the code while maintaining an existing specification.  Some specifications within an area can be changed, but those should be anchored to some other higher level specifications that will not be changed.  LLMs can continuously reassess the original specification (the code before the refactor) to understand the end goal.

Imagine a simple prompt:  Remove tailwind and replace it with custom CSS

This is a lot of work, yes, but like most tech debt / refactoring it is a large amount of work for a small conceptual change.  This is the opposite of feature development, where large amounts of information may be needed to be given to the LLM to make smaller code changes.

LLMs completely change the game when it comes to tackling tech debt.  You can start with having them tackle automated business testing (aka real end to end tests) first (often a technical debt item of many teams).  Then that will give you a way to score the refactor.

This is one of the reasons that I believe the [Application Architect](../concepts/application-architect.md) should have more autonomy, they should be able to prioritize tackling tech debt that enables the agentic harness to stay grounded.
