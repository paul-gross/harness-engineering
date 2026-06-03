# Walk, Run, Wheels, Rocket into Space!

The analogy is simple. First we crawl, then we walk, then we run, then we *sprint*.  You've heard it before.

It's a fun analogy because of Scrum and sprints.

We're not sprinting anymore.  Sprinting is the idea that we expend energy to move at a certain rate along the path.  When we stop spending energy, we stop moving.

With LLMs, we're doing one of two things:

* We're sprinting with [exoskeletons](https://wiki.factorio.com/Exoskeleton) -- We still invest X energy to get Y result, but we do it 30% faster
* We've got [wheels](https://wiki.factorio.com/Locomotive) -- We invest X energy to move at a rate of Y/second.

At its core, it's the difference between how high a line goes on a graph and the area under a curve.  Yeah, the area under the curve is going to be a lot bigger.

## Rocket Into Space?

The first vibe coders strapped a two core ion thruster engine onto their boots and just began flying around in the air.  They're completely out of control, going every which way.  But the most important thing to remember here, is they are **flying** and they are getting a lot further than anyone was getting when they were *sprinting*.  The problem is that they have no idea what is being built under the hood, they aren't grounded, and we don't really know if they're going to be able to land safely.  We assume not.  I think that is a safe assumption.

In a world where SLAs exist, you have paying customers, and you're not just operating in AI Theater, flying is not a realistic approach.

It's also inevitably true that pure vibe coding is a positive feedback loop for system instability and complexity.  If it wasn't, we wouldn't be talking about harness engineering.

## The real analogy, we have wheels

We're not sprinting anymore, we have wheels.  And wheels change the game.  Maybe we're like Fred Flintstone, kicking the ground to move forward.  That's still good.  Maybe we've got a Ford Model T, we're cruising.  Maybe we've gotten as far as getting a Honda Accord.  It's a nice ride, luxurious, with heated seats.  Wherever we are on our journey, our goal is simple -- we want to go faster.  Or as my Factorio friends would always say, "Moar, faster!"

As we go faster and faster with agentic development, we will feel [upward forces I call Lift](./lift.md).  We'll begin to feel the urge to let the LLM generated code be pushed out without thoroughly reviewing it.  "It looks good, I think it works."  The act of letting go is tough.  Once you let go, you are signing off and saying "I approve this work, I am responsible for it, but I trusted an LLM to generate it correctly."  That's very powerful.  But it can also be very dangerous if you have no agentic harness, no quality controls, and the work you are signing off as would generally be identified as AI slop.

No matter what you are in this world, if you go fast enough you will experience lift.  It's not physics, not really, but you get the point.  There is a limit to how fast you can go before that force becomes your barrier.  One of the secondary responsibilities of Harness Engineering is to continually push the maximum velocity that the team can attain without lift.

## [Architects and Harness Engineering](./architects-and-harness-engineering.md)

* The [Harness Engineer](./harness-engineer.md) focuses on velocity.
* The [Application Architect](./application-architect.md) focuses on aerodynamics.

The analogy breaks down when you try to cross physics over to software development, so just leave it alone and don't think too hard about it.

## Rocket boosters, but not into space

My personal goal is to have the most amazing rocket boosters on my [agent harness](./harness-components.md) that I can possibly get.  I want to get to a point where I can...

* Write minimal prompts
* Have minimal tweaks to the planning process
* Have high confidence in the LLM output
* Spend minimal time reviewing the code while fully understanding the system and changes taking place

Everyone wants this, right?  Go fast and stay grounded.
