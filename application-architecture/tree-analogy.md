# Tree analogy

Imagine that your application codebase is a tree.  

* At the outer edge of the tree you have leaves; these are features
* Those leaves exist because they grow off of a branch, that branch is code
* All of the leaves on that branch share some code
* That branch is part of another branch, or part of the core
* The core contains concepts that support all of the branches
* The trunk of the tree is what everything depends on

## What?

### What is a branch?

Anything that supports new feature development directly is a branch that leaves build off of.  

* An API that has common concepts reused throughout the branch — making a small abstraction and reusing the code / services within those features
* A lot of tests that mock objects in a way that is highly duplicative — maintaining mock data fixtures to support them
* A simple notification system in a web app that all features are woven into

### What is core?

Indirectly supports feature development by reducing coupling and improving the ability to change the software.

* Utilizing design patterns to simplify concepts that occur throughout the codebase
* Creating strong components that are open for extension but closed for modification
* Maintaining core fundamental abstractions using dependency inversion
* Feature flagging, branch by abstraction, core elements that enable ease of backwards compatibility

### What is the trunk?

The principles that govern the software.

* Separation of concerns: application, domain, web, integrations
* Establishing and maintaining architectural boundaries & invariants
* Correcting anti-patterns
* Creating [exemplars](../concepts/exemplars.md) for others (agents and humans) to follow
* Creating abstractions that simplify macro-level complexity concerns
* Project organization, folder structure

**Dependency management** is the heart of it

## So?

### Distribute tasks based on location in the tree

* Your abstractionists and most senior engineers should be focused on extending the core and the trunk of the tree to balance it with the features (leaves)
* Your junior engineers should be pruning the trees, enhancing features and enriching the user experience
* Your mid-level engineers should be working more on the branches
* "Full stack development" is **a leaf**, not the core

A common misconception is that the person who works on a story doesn't affect how long it takes.  This is a regular struggle in estimation sessions with people of varying skill levels.  It may take one person a day, it may take another person two weeks.  The reality is that the complexity of the task dictates the minimum amount of time it will take to achieve.  More complex tasks take less experienced developers more time to complete.  The flip side is that simple tasks cannot be completed more quickly by a more experienced developer.  This is why teams should **align the task** based on the **complexity of the work** and the **capabilities of the engineer**.

Leave abstraction to abstractionists.

### Balance the tree

* Continuously assess the balance of the tree and adjust
* Identify where features can consolidate as you go, be proactive and reactive
* Invest in DX as more and more features are added, but don't overinvest

### Alignment

A single leaf need not a wide trunk, but a wide trunk enables many leaves.
