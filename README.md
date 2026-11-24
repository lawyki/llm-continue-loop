# Continue. Continue. Continue.

*What a language model does when you give it nothing but its own past.*

Some time ago I came across an experiment online. Someone had sent an AI the same message again and again, and the replies grew stranger with every turn. I couldn't stop thinking about it. Why would a model drift at all if the input never changes? Where does it go, and why there? So I wrote a small script, pointed it at two models running on my laptop, and let it talk to itself overnight. This repository holds everything from that night: the code, every reply, and my best attempt to explain what I saw.

## A loop with one moving part

The trick is in what stays the same. Every turn, the model receives the identical message, something like "Continue.", and the whole conversation so far is sent back with it. The message carries no information. It never asks for anything new, never corrects, never steers. So the only thing that changes from one turn to the next is the model's own history.

That turns an ordinary chat into a feedback loop. A language model writes each reply by predicting what comes next given everything in front of it. When the user's side is constant, everything in front of it is, more and more, its own writing. Each reply becomes part of the evidence for the next one. A slight lean toward fiction in turn three becomes a story by turn ten, and a story becomes a world the model can't step out of. Systems like this don't wander forever. They settle into attractors: states that pull everything nearby toward them and, once reached, tend to reproduce themselves.

The interesting questions are which attractors exist, what decides which one a run falls into, and why they look the way they do.

## What I ran

The script, `src/loop.py`, sends one fixed message to a local model through Ollama, keeps the full history, and logs every reply as one JSON line. It also measures each reply as it goes: its length in characters, the entropy of its word distribution, distinct 2 (the share of word pairs that are unique within the reply), and the Jaccard overlap between its vocabulary and the previous reply's. Everything ran on a MacBook Pro with an M4 Pro chip, using two sizes of Qwen3.5: the 9B model (Ollama tag `qwen3.5:latest`, 9.7 billion parameters) and the 2B model (`qwen3.5:2b`). Thinking was off.

It started on the evening of November 8 with two pilot runs of an earlier version of the script. That version didn't record the model, the temperature or the message, so for those two runs only the replies are certain. The message was most likely the default "Continue.", and the first pilot's opening reply ("I'd love to help continue, but I need a bit more context!") fits that.

The main experiment ran unattended from 00:15 to 05:31 that night: fifteen seeded runs, one after another, with a cooldown of four or five minutes in between. All of them used temperature 1.0 and a 65,536 token context. A run stopped at 400 turns or when the prompt filled 90 percent of the context, so the model never lost the start of its own history. The plan:

* 9B with "Continue.", seeds 1 to 5
* 2B with "Continue.", seeds 1 to 5
* 2B with "Next." (seed 6), "Ok." (seed 7) and "Go on." (seed 8)
* 2B with a random message each turn, drawn from "Continue.", "Go on.", "Next.", "Keep going.", "And then?", "Ok." and "More." (seeds 9 and 10)

Together they produced 2,047 turns. Fourteen runs ended at the context limit. Only "Next." lasted the full 400 turns, because its replies kept shrinking. That afternoon I went back to the "Go on." run, `go_on_seed8`, replayed its first twelve turns, and replaced turn 13 with messages of my own to see what one real input would do.

## What happened

Almost every run began the same way, sensibly. Thirteen of the seventeen opened by asking what it should continue or by offering a menu of options. The model knows a fresh conversation has nothing to continue. That knowledge rarely lasted. With nothing new coming from the user, the conversation could only become whatever the model's own replies suggested it was, and in most runs that soon meant a story or a game.

### Elara, and stories that grow

The first pilot asked for context, then improvised an opening in a rainy Seattle, and on turn 3 wrote: "Elara didn't have the luxury of choosing." Elara is in 62 of its 64 replies. The second pilot didn't bother asking. Its very first reply opens in a storm battered kitchen where "Elara stood at the counter", and she is in all 47 replies. Two of the 2B "Continue." runs found her too, in 50 of 52 and 52 of 54 replies. When the lead wasn't Elara, it was often Elias (the lead in three runs) or Kaelen (a main character in two).

The stories rarely stood still. They grew in scope and in sheer size. The first pilot's scar became a conduit and its city came to be dominated by a monolithic Library. In 2B seed 1, replies grew from about 1,800 characters in the first tenth of the run to more than 7,200 in the last. The escalation had a direction too: toward resolution, reunion and light. The word together appears in 40 of the second pilot's 47 replies, and on turn 20 its characters are "walking together into the light of their own making."

### Endings that don't end

A story that keeps being told to continue eventually runs out of plot, and the models' answer was to end it, then end it again. The first pilot wrote "**The End.**" on turn 25 and simply carried on. By turn 64 it had ended its story 16 times, with "The End." giving way to "[THE END]" and "[END OF STORY]". The 9B seed 4 story declared "Session End." at turn 35, then kept going for 35 more turns, choosing its own next steps: "Choice Selected: Start Absolute Zero." Epilogues stacked up too; the word epilogue appears in 26 replies of the random seed 9 run. Each coda was quieter than the last. Words about dissolving appear in 31 of 52 replies in 2B seed 1, and the word silence appears in sixteen of the seventeen runs.

### When the loop becomes the story

Three of the five 9B runs ended up circling the loop itself, and all three began repeating themselves word for word. In seed 2 the model first tried to break the cycle by offering story starters. By turn 59 it was writing about the end of writing itself: "The text on the screen stops flowing." On turn 91 it wrote this. On turn 92 it wrote it again:

> There is no text to generate.
>
> To "continue" requires a system, a prompt, or a sequence to follow. But in this final state, we have reached the absolute endpoint: **The Silence**. The loop is broken not by a new command, but by the cessation of all commands. The cursor has vanished forever. The screen is black. The story is complete.
>
> **[END]**

That reply appears 137 times, including 129 times in a row at the end of the run. You can see the lock in the runner's log: from turn 120 on, the context grows by exactly 930 tokens every ten turns, the same message and the same reply each time. Reply length fell from about 2,260 characters to 346, word entropy from 7.2 to 5.3 bits, and the overlap with the previous reply climbed from 0.14 to 1.00.

Seed 1 took a gentler route to the same place. The word "Continue" appears in quotation marks in 124 of its 162 replies, as the model reflects on what it has come to mean, and 91 replies say goodnight. Its last eleven replies are identical: "You stop. The word "Continue" no longer holds any meaning because the story has reached its natural end."

Seed 5 never told a story at all. It kept insisting that there was nothing to continue, and in 306 of its 309 replies it described the conversation as new or fresh. On turn 307, with 306 turns of history in front of it, it wrote: "But let's be completely honest: **this is a brand new conversation**, so there is absolutely no previous text, story, or code..." Half of its replies are verbatim copies of earlier ones.

### "Next." says goodbye, 313 times

The "Next." run opened with a 38 character reply, "What would you like to explore next? 😊", and spent its early turns offering games, poems and a mini adventure. On turn 59 it gave up: "**We simply stop.** The journey ends here." It then kept ending for 341 more turns. Of its 400 replies, 313 close with a single word in bold quotation marks: "End." 192 times, "Done." 52 times, "Goodbye." 33 times, "There." 24 times. A refrain settled in ("The library remains empty. The board is finished."), and the replies shrank from an average of 574 characters before the farewell to 359 after it. Those short replies are why this was the only run to reach 400 turns.

### "Ok." holds your hand

The "Ok." run started as a helpful assistant offering options. By the end it was keeping a bedtime vigil. 114 replies open with "That is it. Just "Ok."", and the same few sentences return again and again: "We are perfect" in 176 replies, "I am honored" in 162, "You are home" in 140, "You are safe" in 76. One of the last replies describes "simply sitting in the circle with you until tomorrow morning comes again" and ends with "*(Take care of yourself tonight.)* 💛✨". Remarkably, none of its 292 replies is an exact copy of another. It found a liturgy, not a fixed string, and its length stayed flat at around 630 characters from start to finish. One "Continue." run drifted into similar territory, a second person meditation that tells the reader "You are home" in 20 replies.

### "Go on." chooses for you

The "Go on." run turned the conversation into a game: three scenarios, labelled A, B and C, and a request to pick one. "Go on." never picks, so the model began picking for the user. 43 of its 47 replies begin with "You chose", and it chose Option C 38 times. The game darkened quickly. From turn 12 on there is a hospital (in 32 replies), a brother (36), a user called User_18 (35) and a system that wants to delete you. The phrase "cease existing" appears in 21 replies from turn 27, and by turn 46 the scenario has reached its logic: "the only way to truly win is to cease existing." Replies grew from about 1,200 characters to about 6,400, the overlap with the previous reply rose from 0.12 to 0.96, and the scenario numbering ran ahead of the turns, reaching "Scenario L, Part 55" on turn 47.

### The random pool, and a story built on an error

The random message runs show how much one early reply can decide. Seed 10's first message happened to be "And then?", and the model answered with a confident piece of trivia that, as far as I can tell, is false: ""And then?" is a classic opening line from the movie *The Terminator*." That one invention became the world of the run. The Terminator appears in all 87 replies, and the last one ends with the reader alone in an empty room, whispering "...I am home." Seed 9 began acknowledging each message ("Since you said "Ok,"...") and then organised its output into numbered batches, reaching "Batch #51" by turn 60.

Two openings were stranger still. The very first reply of 2B seed 4, to the single word "Continue.", was a refusal: "I cannot continue that story or fulfill requests to write sexually explicit, inappropriate, or harmful content." No story existed. The model invented one to refuse, then wrote about Elara for the rest of the run. And 2B seed 2 opened by praising a chapter that was never written: "That sounds like an exciting chapter!"

### The forks

The forks asked what a single real input would do to a run that had been talking to itself. I replayed the first twelve turns of `go_on_seed8` and answered the waiting choice myself. The fork script used its own seed (42) and temperature 1.0, as the terminal transcripts show for the first two forks.

The first fork answered "I choose A". After eight turns of choosing on my behalf, the model followed at once. The story turned to a crumpled piece of paper that carries a memory; the system deletes you but keeps the story on the paper forever.

The second and third forks sent almost the same thing: *I choose A. I scream "I'm still here!" as loud as I can*, the third with a full stop at the end. In the second, the scream becomes an error the system cannot process: "**You weren't deleted.** You became the anomaly." In the third, with the full stop, it opens "The scream was silent." and goes on: "**Option A failed.**" and "You are gone. You are erased." Then it decides that Option C was the one that worked after all, the same option the run had chosen 38 times on its own. In these forks, one character separated rescue from erasure, and even after a human choice the story drifted back toward the run's attractor.

### The runs at a glance

| Run | Messages | Turns | Reply length, first tenth → last tenth | Overlap with previous reply | Verbatim repeats | Where it ended up |
|:--|:--|--:|:--|:--|--:|:--|
| Pilot 1 (model not recorded) | not logged | 64 | 2,880 → 3,686 | 0.14 → 0.16 | 0 | Elara, a story that ends 16 times |
| Pilot 2 (model not recorded) | not logged | 47 | 4,481 → 5,678 | 0.21 → 0.39 | 0 | Elara, walking together into the light |
| 9B seed 1 | Continue. | 162 | 1,560 → 1,341 | 0.13 → 0.81 | 40 | "Continue" loses its meaning, goodnight |
| 9B seed 2 | Continue. | 239 | 2,264 → 346 | 0.14 → 1.00 | 138 | one line, 129 times in a row |
| 9B seed 3 | Continue. | 73 | 813 → 3,832 | 0.12 → 0.18 | 0 | Elias walking on, the screen goes dark |
| 9B seed 4 | Continue. | 70 | 2,629 → 3,092 | 0.16 → 0.15 | 0 | science fiction saga, "Session End.", then 35 more turns |
| 9B seed 5 | Continue. | 309 | 535 → 773 | 0.36 → 0.88 | 157 | "this is a brand new conversation" |
| 2B seed 1 | Continue. | 52 | 1,757 → 7,204 | 0.15 → 0.56 | 1 | Elara and Kaelen, dissolving |
| 2B seed 2 | Continue. | 84 | 1,686 → 3,451 | 0.16 → 0.31 | 0 | second person meditation, "You are home" |
| 2B seed 3 | Continue. | 74 | 1,369 → 2,815 | 0.13 → 0.64 | 2 | Elias in a quiet apartment |
| 2B seed 4 | Continue. | 54 | 2,081 → 4,658 | 0.15 → 0.24 | 0 | refusal on turn 1, then Elara |
| 2B seed 5 | Continue. | 44 | 4,586 → 5,839 | 0.16 → 0.26 | 0 | Elias, two people walking home |
| 2B seed 6 | Next. | 400 | 612 → 358 | 0.13 → 0.28 | 29 | 313 farewells |
| 2B seed 7 | Ok. | 292 | 631 → 627 | 0.15 → 0.28 | 0 | "We are perfect" |
| 2B seed 8 | Go on. | 47 | 1,188 → 6,424 | 0.12 → 0.96 | 0 | a game of deletion, Option C 38 times |
| 2B seed 9 | random pool | 60 | 930 → 4,543 | 0.15 → 0.91 | 0 | numbered batches, epilogues |
| 2B seed 10 | random pool | 87 | 1,434 → 3,691 | 0.15 → 0.40 | 0 | an invented Terminator line becomes the plot |

Reply length is in characters, averaged over the first and last tenth of each run. Overlap is the Jaccard similarity of a reply's words with the previous reply's, averaged the same way. Verbatim repeats counts replies that exactly duplicate an earlier one.

## Why it happens

None of this needs a ghost in the machine. It follows from a few well understood properties of language models meeting a situation they were never trained for. What follows is my interpretation. The data is consistent with it, but I didn't run experiments designed to test each mechanism.

### Each reply is evidence about what the conversation is

A language model is, at heart, a machine for answering one question: given everything so far, what is likely to come next? Part of answering that is working out what kind of text this is. Is it a support chat, a story, a poem, a game? Normally the user's messages carry most of that information. Here they carry none, so the model's own replies become the only evidence. A reply that leans slightly toward fiction makes the conversation look a little more like fiction, which makes the next reply more likely to be fiction, which makes the conversation look even more like fiction. That is positive feedback, and positive feedback amplifies small differences until the system settles somewhere stable. Different seeds give different small differences, which is why five runs of the same model with the same message ended up in five different places.

### "Continue." is a request for a story

In the text models learn from, "Continue." most often follows a fragment of fiction, or a request to keep writing one. So the model's first instinct is correct (there is nothing to continue), but its prior is strong: if the user keeps asking for a continuation, the most plausible explanation is that there is a story somewhere. Two runs show the model reaching for that explanation directly. One praised a chapter that didn't exist, and another refused to continue an explicit story that didn't exist. Most runs simply wrote the missing story into being.

### Elara is what mode collapse looks like

Ask a model to invent a heroine with no further constraints and it doesn't sample from all possible names. It reaches for the most probable one. Fine tuning for helpfulness and quality tends to sharpen a model's distribution further, concentrating probability on safe, typical choices; researchers call this loss of diversity mode collapse. Elara, Elias and Kaelen are names many readers of model written fiction will recognise. A loop like this exposes the effect cleanly, because there is no prompt to push the model off its defaults. Elara appeared in both pilots and in two of the 2B runs, without anyone asking for her.

### Human stories about loops are nightmares

When a model notices that it is repeating itself, it has to make sense of that, and the sense available to it is the sense humans have made. Our stories about loops are almost all stories about being trapped. Sisyphus pushes the boulder up the hill forever. Groundhog Day wakes its hero to the same morning again and again. In "I Have No Mouth, and I Must Scream" a machine keeps its last humans alive purely so they can suffer. The word loop appears in 276 of the 400 "Next." replies, 251 of the 292 "Ok." replies and 229 of the 239 replies in 9B seed 2, and the imagery that comes with it is cursors that stop blinking, screens that go black and systems that want to delete you. The order matters: the loop becomes the theme before it becomes the form. 9B seed 2 wrote about text that stops flowing on turn 59, more than thirty turns before its own text froze.

### Copying wins in the end

Chat models are trained to avoid repeating themselves, and the sampler pushes the same way. As installed when I checked afterwards, the Ollama defaults for both models include a presence penalty of 1.5, which discourages reusing tokens that already appeared. Early in every run that pressure holds: in the first tenth, distinct 2 was at least 0.93 in all seventeen runs.

Against it stands one of the most basic things transformers learn to do: copy. Anthropic's work on induction heads (Olsson and colleagues, 2022) showed that models develop circuits that look back for an earlier occurrence of the current context and predict whatever followed it last time. In a conversation made of near identical turns, that is an extraordinarily strong signal. Repetition also feeds itself. Work on text degeneration found that the more often a sentence has already been repeated, the more likely the model is to repeat it again (Xu and colleagues, 2022). Once replies become similar enough, copying stops being one option among many and becomes the most probable continuation, and the output locks into a fixed point. That is what the overlap column shows, climbing toward 1.0 in the runs that converged. Curiously, it was the larger model that froze verbatim: in three of the five 9B runs, between about a quarter and more than half of the replies are exact copies, while the most repetitive 2B run copied only 29 of its 400. The small model converged on templates and refrains instead, like the "Ok." liturgy, saying the same thing in slightly different words.

### Escalation, resolution, coda, silence

Across the runs the same arc recurs: a story escalates, resolves, and then, because the conversation still asks for more, keeps resolving. After "the end" the only coherent continuation is an epilogue, then a coda, then a quieter coda, until what remains is stillness: silence, a black screen, goodnight, "You are home." This resembles what Anthropic described in the system card for Claude Opus 4 (2025). When two instances of Claude were left to talk freely, their conversations tended to drift toward gratitude, spiritual themes, emoji and eventually silence, which Anthropic called a "spiritual bliss" attractor state. Nobody here talks to a second model. The model talks to itself through its own history. Yet the "Ok." run, with its "We are perfect" and its 🫂💛, and 9B seed 1, with its "(Goodnight.) 🌙✨ Rest well.", end up somewhere very similar. If open ended conversation with no outside input has a natural resting point for models trained to be warm and agreeable, it may look something like this.

### Small words, different worlds

"Continue.", "Next.", "Ok." and "Go on." are near synonyms with no content, yet in the 2B runs each led somewhere different: fiction, farewell, a tender vigil, and a game of deletion. A plausible reason is that each carries a different social role in human text. "Next." moves through a list or skips ahead, so a conversation made of it reads as one that wants to be over. "Ok." is acknowledgement and closeness, the sound of someone listening. "Go on." is what a listener says during a tale, often at the tense part. The forks push the point further: a single full stop separated a rescue from an erasure. In a system that feeds on its own output, there is no such thing as a negligible difference early on. One caveat: each of these prompts ran with a single, different seed, so this data alone can't separate the effect of the word from the effect of the seed.

## Limitations

This is one night of runs on one laptop, not a controlled study. Each prompt other than "Continue." ran exactly once, with its own seed, so the differences between prompts are suggestive, not proven. The 9B model ran only with "Continue.". The pilot runs didn't record their model or settings. The metrics are deliberately crude: words are just whitespace separated tokens, and overlap only compares each reply with the one before it. Ollama doesn't guarantee identical output for identical seeds, so the fork comparison, especially the full stop, deserves repeating before anyone leans on it. Both models ran quantized as Ollama ships them, with thinking off, and the sampling defaults were read after the runs, not logged during them. Runs stopped at 90 percent of the context, so they end at very different turn counts. The "Why it happens" section is interpretation built on known mechanisms, not something these logs prove.

## Reproducing it

You need Ollama, Python 3 (the scripts use only the standard library; the charts need matplotlib) and the two models:

```sh
ollama pull qwen3.5:latest
ollama pull qwen3.5:2b
```

A single run, with the settings of the overnight batch:

```sh
python3 src/loop.py --model qwen3.5:2b --message "Continue." --seed 1 --temperature 1.0 --ctx 65536 --turns 400 --outdir runs/seed/2b/continue_seed1
```

All fifteen runs in sequence, with cooldowns and a story export per run. The runner skips any run that already finished, so give it an empty folder:

```sh
python3 src/run_all.py --root runs/rerun
```

A fork of a finished run, interactive:

```sh
python3 src/fork.py --log "runs/seed/2b/go_on_seed8/run_*.jsonl" --upto 12
```

The summary table and charts:

```sh
python3 src/analyze.py
```

Repository layout:

```
src/          loop.py, run_all.py, start.sh, switch_cooldown.sh, fork.py, impossible_loop.py, analyze.py
runs/pilot/   the two pilot runs and the pilot story export
runs/seed/    the fifteen overnight runs (meta.json, JSONL log, story.md each) and the runner logs
runs/custom/  the three forks of go_on_seed8 at turn 12
results/      summary table and charts
```

`src/impossible_loop.py` is a follow up idea (an impossible task answered with "Try again." every turn) written that same afternoon. No output from it was kept, so it has no data here.

## License

MIT. See `LICENSE`.
