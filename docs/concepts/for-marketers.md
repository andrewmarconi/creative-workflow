---
author: Andrew Marconi
---

# Marketer's Guide to Gen AI

*by Andrew Marconi* - 10 Feb, 2026

If you've been in a marketing meeting in the past few years, you've heard the buzzwords: *generative AI*, *LoRA,* *checkpoint,* *stable diffusion.* If you don't have a technical background, it sounds like engineering gibberish -- and I bet you've included those buzzwords in a pitch deck and just prayed the potential client didn't ask what they mean.

The good news? You don't need to know how to build the engine to drive the car. You just need to know what the buttons do. Stop trying to understand Generative AI as complex software and math (even if it is). It makes more sense if you treat it like a massive, slightly chaotic freelance digital creative agency that helps you level-up. Here's the org chart.

## The Talent: The Model (or "Checkpoint")

**Every agency is built around its talent.** In generative AI, that's the model (often called a checkpoint). This is your Generalist Artist. They've seen billions of images; they know what a dog looks like, who Van Gogh is, and the visual shorthand for "cyberpunk city."

For a marketer, picking a model is kind of like casting an illustrator. It sets the baseline vibe. If you need photorealistic product shots, you hire a realist (models like Juggernaut or Realistic Vision). If you want 3D Pixar-style characters, you hire a stylist (but consider important rights and usage issues I address below). You wouldn't ask an anime artist to paint a serious corporate portrait of your CEO. Don't ask a stylized AI model to do it, either. Pick the talent that fits the brief.

## The Account Exec: CLIP

The problem with your Artist (the model) is that they don't speak English. They speak math -- really complex matrix mathematics. If you type "A blue sneaker on a beach," the Artist stares at you blankly. That's where CLIP comes in. CLIP, or "contrastive language–image pre-training" is the agency's Account Executive. Their entire job is to take your client brief (the prompt), figure out the nuance, and translate it into the mathematical vectors the Artist understands.

When the AI fails to get your vision, it's usually a translation error here. CLIP is smart, but literal. If you just say "Apple," it doesn't know if you want the fruit or the laptop. That's on you to clarify in the brief.

## The Process: UNet

Once the brief is translated, how does the work get done? The Artist doesn't just print a finished image instantly. They start with a fuzzy mess of static noise and slowly refine it. UNet is the brain managing this sketching process. It looks at the static and asks, "Is that a pixel of a nose? Or a cloud?" over and over again. It "denoises" the image step-by-step until a clear picture emerges. That's why generation takes a few seconds—you are watching the sketch turn into a painting in real time.

## The Delivery: VAE

The UNet works in a "latent space" \- a mathematical representation of complex information that looks like garbage to the human eye. It's the back-of-house kitchen. The VAE (variational autoencoder) is the waiter. It takes the finished dish from the kitchen and puts it on the plate (pixels on your screen). If your images ever look washed out, grey, or foggy, the VAE is usually the culprit. The food was cooked right, but the waiter dropped it on the way to you (not a perfect analogy, but pretty close).

## The Specialists (The Add-ons)

The base Artist is good, but they're a generalist. Sometimes, the campaign needs a specialist. In generative AI, these are plug-ins you snap onto the main model to force it to behave.

### The Brand Cop: LoRA

Your Generalist Artist doesn't know your specific brand mascot, and they definitely don't know the hex code for your packaging. A LoRA (standing for "low-rank adaptation") is your freelance Brand Consultant. It's a tiny file -- a "mini-brain" that plugs into the main model. It effectively says, "I know you know how to draw a soda can, but this is exactly how the Coca-Cola logo looks."

Marketers love LoRAs because they let you train the AI on a specific product, influencer face, or art style without the massive cost of retraining the whole model. **It's your brand style guide, digitized.**

### The Art Director: ControlNet

If you prompt "A woman holding a coffee cup," the model might put the cup in her left hand, right hand, or balance it on her head. It's creative, but chaotic. ControlNet is the Art Director. It lets you hand the AI a rigid structure, like a stick-figure drawing, a depth map, or a specific pose, and say, "Paint whatever you want, but the subject MUST stand in this exact position."

**This is the killer feature for campaigns.** You can use ControlNet OpenPose to make a model match a viral TikTok dance exactly, or LineArt to hide your logo subliminally in a landscape. It gives you the composition control that text prompts never will.

### The Mood Board: IP-Adapter

Sometimes, words fail. You don't want to describe "a futuristic, shiny, chrome texture with blue undertones." You just want to point at a picture and say, "Make it look like this." IP-Adapters (meaning, "image prompt" not "intellectual property") let you use an image as a prompt. Instead of typing, you upload a reference photo. The AI looks at it and pulls the style, structure, or face into the new creation. It's the ultimate mood board. Use it for style transfer like making your CEO look like a superhero by referencing a comic book cover or just to ensure the shoe in the generated image actually looks like the shoe you sell.

## The Production Studio: Video & Audio

Recently, the agency expanded. We aren't just doing print ads anymore; we're moving into social video, radio and even broadcast.

### The Continuity Director: Temporal Consistency (Video AI)

I'm sure you've seen videos where a person eats spaghetti and the pasta turns into fingers or the fork melts (if not, [have a look at a video I generated](https://www.instagram.com/p/DBbf4QNgFMW/) a while back). That's a failure of Temporal Consistency.

[![Temporal consistency failure in AI-generated video](/_static/generative-ai-temporal-consistency.jpg)](https://www.instagram.com/p/DBbf4QNgFMW/)

Video is just multiple still images played every second. The hard part isn't painting one nice image; it's painting 24 of them in a row where the shirt color doesn't change and the face doesn't melt.

Think of Temporal Consistency as the Continuity Director on a movie set. Their job is ensuring that if the actor holds a cup in frame 1, it doesn't teleport to their other hand in frame 2. Tools like Runway Gen-3 or Sora are essentially models with much better Continuity Directors. For marketers, this matters more than resolution. A blurry video is usable; a video where your product morphs into a cat is not.

### The Sound Engineer: Generative Audio

Finally, the sound booth. This includes TTS (Text-to-Speech) and Music Generation. Think of this as an on-demand Foley Artist and Composer. In the past, fixing a line of dialogue meant booking a studio and a voice actor. Now, with generative voice, you clone the narrator's voice and fix the script by typing.

Historically, this space was dominated by expensive, proprietary tools like ElevenLabs -- great quality, but you pay for every second. But the landscape is shifting fast. Open models like Alibaba's Qwen3-TTS are now becoming available. They are powerful, free-to-use "sound engineers" you can run on your own servers. They rival the paid giants, allowing brands to generate studio-quality, emotive voiceovers without the per-second meter running. It's the difference between renting the studio by the hour and buying the equipment yourself.

## Equity & Legal Rules of Engagement

Every agency has rules. Before you unleash this team on your next campaign, remember two things:

### The Creative Director is Human (generative AI has no sense of taste)

It's easy to look at this list and think the AI does everything. It doesn't. Generative AI is a high-speed synthesizer. It generates options at lightning speed, but it lacks taste, intent, and strategy. It doesn't know why a blue background works better for your Q3 demographic; it just knows how to make pixels blue because that's what it has seen before.

Your designers and copywriters are more important than ever, but their roles are shifting. They're becoming curators and refiners. You need a human pro to look at the 50 images the AI spit out, pick the one that fits the strategy, and fix the six weird fingers. The AI provides the raw materials; the human provides the soul.

### Rights Management: Respect & Compensation Still Matter

**Just because you can clone a voice doesn't mean you should.** It's about more than legality; it's about respecting the craft. If you use a LoRA to generate an image based on a specific person, or clone a narrator's voice, you are using their personal brand. Treat AI talent like human talent. If you train a model on a face or voice, pay them for it. A model release isn't just paperwork; it's an agreement on boundaries. New tech, old rules: **Great work requires fair partnerships.**

## The Frontier: Building Your Own Lab

One final truth: this "digital agency" is always under construction. The rate of innovation is wild -- yesterday's miracle is today's standard feature. To survive the chaos, you don't just need tools; you need a workbench. You need a place to break things and test these capabilities before you bet a client campaign on them.

### The Traffic Dept: TVC Adaptation

The piece I'm especially proud of is the TVC Adaptation tool. It uses a tool called LangGraph—think of it as the agency's Traffic Department. It mirrors the real creative process. A source script is handed off to a set of AI "agents" that extract concepts and cultural nuances. They pass that brief to an LLM "Copywriter." Once the adapted script is written, it goes to a series of "Proofreaders" who check for formatting, cultural fit, and brand adherence with the intent of ideation and first revision of concepts (not final output).

Again, this isn't about replacing the creative team or the agency; it's about empowering them to move faster and try new ideas they haven't thought of before. It's about taking a beautiful TVC film based in the US market and adapting it to the cultural nuances of 200 global markets instead of just two because of resources. Don't like the result? Adjust the prompt, swap the model, or use the draft as a base to write the perfect version yourself.
