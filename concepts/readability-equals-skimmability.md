# Readability = skimmability

Information digestion is the focus of optimization.

The rate at which we find and gather information has been transformed this decade.  It's no longer oriented around what you know, it's also now about how fast you can find out what you need to know.

Yes, what the web of information that makes up your intuition is also important.  It's just not all about your ability to add to that intuition.

## What?

In my early years as a software developer, I remember people telling me that my emails were **dense**.  "They're good, but they have a lot to them."  After many years, I began to understand that generic content that is sent to multiple people is sub-optimal, but necessary.  Each consumer wants to understand and know only the parts of that content that are relevant to their agenda.  A series of large paragraphs is not effective when each party is only interested in one small part of that paragraph.  It's just not realistic to curate a custom message to a web of people who need to know all of the different pieces of information.  Furthermore, there is [something about the blue eyed](https://xkcd.com/blue_eyes.html) that is equally as important there.

* The feedback?  "It's not very readable, break it up into bullet points."
* Bullet points are easier to read and digest
* Translation: Bullet points are easier to **skim**
* **Readability** = **Skimmability**

Content should be designed not to be read in its entirety, but instead to be cherry-picked.

## The art of markdown, headers, paragraphs, and bullets

* **Concise**: Keep each bullet point concise, use a **bold statement** followed by further description
* **Discoverability**: Headers, subheaders, bullets (main point and verbose description), and paragraphs are just a tree structure for O(log n) retrieval
* **Agents love skimmability**: It's not just about O(log n) retrieval, it's about context management -- only draw what is relevant to the task

Paragraphs can be useful to convey additional details when bullets don't suffice.  You cannot convey concepts entirely from bullets alone.  At some point, a large block of information is going to be necessary to provide the understanding relevant to the topic.  That can be accompanied by additional details, examples, etc, but must not be composed in a way that duplicates the concept.  This is where Markdown Links, or [progressive disclosure of information](./progressive-disclosure.md), begins to arise.

* **[Digital garden](./digital-garden.md)**: Organizing concepts into markdown files that link to each other helps convey interconnected system concepts without concept duplication
* **Information slices**: A well organized markdown based digital garden can be processed into an information slice, where an understanding is drawn from many small parts of many markdown files.
* **Cross-concept conversations**:  An Agent is incredible at constructing information slices and presenting them to the user (you) or another agent (the developer) to answer a specific question or solve a specific problem.

These are the core elements of harness engineering.  Build a digital garden that answers all of the questions *without reverse engineering the code*.

## Harness Engineering and Skimmability

AI is amnesiac. It always starts with the same intuition.  Optimizing the information relevant to their job in a manner that is highly skimmable, deep, and digestible is critical.

* **Markdown patterns**: Patterns in the markdown structure itself can aid in skimmability (reused templates or section names provide general ideas on what to expect)
* **Less is more**:  Context management was immediately identified as the name of the game and that is universally accepted
* [Overloaded terms & thematic aliasing](./overloaded-terms.md): Software overloads many terms (like Architecture or Service) which cause confusion and misinterpretation
