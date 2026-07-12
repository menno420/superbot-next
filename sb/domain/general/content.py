"""General-subsystem content pools — the shipped random-pick surface
(disbot/cogs/general_cog.py over disbot/data/json/general_content.json).

Provenance discipline: every entry below is ORACLE-VERBATIM, reconstructed
fragment-by-fragment (menno420/superbot @ e7957fa1 search_code chain, each
fragment overlapping its neighbours):

* ``FACTS``/``JOKES``/``QUOTES``/``TRIVIA`` are the four
  ``data/json/general_content.json`` arrays, complete and IN ORDER —
  25 entries each (the file carries exactly these four keys; trivia rows
  keep the shipped ``question || answer`` separator verbatim).
* ``GREETINGS``/``MOTIVATIONS``/``EIGHTBALL`` never lived in the JSON —
  they are the cog's own module constants (``GREETINGS``/``MOTIVATIONS``
  lists and the 8-ball answers list), 5/5/8 entries.

ORDER AND LENGTH ARE LOAD-BEARING: the prefix commands draw
``random.choice`` on the module-global stream the parity runner reseeds
per case (seed 42), so the drawn INDEX (a function of pool length) and the
entry AT that index are both golden-pinned (goldens/general/sweep_fact et
al: len-25 pools draw index 20, len-5 index 0, len-8 index 1) — and the
draw count shifts the FOLLOWING chat-XP ``randint`` (see
sb/manifest/general.py). Never reorder, insert, or drop entries without
re-verifying every general golden.
"""

from __future__ import annotations

import random

__all__ = [
    "EIGHTBALL",
    "FACTS",
    "GREETINGS",
    "JOKES",
    "MOTIVATIONS",
    "QUOTES",
    "TRIVIA",
    "pick",
]

# oracle-verbatim (general_content.json "facts", complete, in order)
FACTS: tuple[str, ...] = (
    "Honey never spoils — archaeologists found 3000-year-old honey in "
    "Egyptian tombs.",
    "Octopuses have three hearts and blue blood.",
    "Bananas are berries, but strawberries aren't.",
    "A day on Venus is longer than a year on Venus.",
    "Cleopatra lived closer in time to the Moon landing than to the "
    "construction of the Great Pyramid.",
    "Water can boil and freeze at the same time — this is called the "
    "triple point.",
    "The Eiffel Tower grows about 15 cm taller in summer due to thermal "
    "expansion.",
    "A group of flamingos is called a flamboyance.",
    "Wombat feces are cube-shaped — the only known animal to produce "
    "cuboid waste.",
    "Sharks are older than trees — sharks appeared roughly 450 million "
    "years ago, trees about 360 million years ago.",
    "The shortest war in recorded history lasted 38 to 45 minutes: the "
    "Anglo-Zanzibar War of 1896.",
    "A jiffy is a real unit of time: 1/100th of a second in electronics.",
    "Sloths can hold their breath longer than dolphins — up to 40 minutes.",
    "There are more possible iterations of a game of chess than there are "
    "atoms in the observable universe.",
    "A snail can sleep for 3 years.",
    "The word 'nerd' was first used by Dr. Seuss in 'If I Ran the Zoo' in "
    "1950.",
    "Crows can recognize human faces and hold grudges.",
    "Butterflies taste with their feet.",
    "The inventor of the Pringles can was buried in one.",
    "Armadillos always give birth to identical quadruplets.",
    "The first computer bug was an actual bug — a moth found in a Harvard "
    "Mark II in 1947.",
    "Penguins propose to their mates with pebbles.",
    "A bolt of lightning contains enough energy to toast about 100,000 "
    "slices of bread.",
    "The hashtag symbol is officially called an octothorpe.",
    "Sea otters hold hands while sleeping so they don't drift apart.",
)

# oracle-verbatim (general_content.json "jokes", complete, in order)
JOKES: tuple[str, ...] = (
    "Why can't skeletons fight each other? They don't have the guts.",
    "I told my doctor I broke my arm in two places. He told me to stop "
    "going to those places.",
    "Why do cows wear bells? Because their horns don't work.",
    "What do you call fake spaghetti? An impasta.",
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Why don't scientists trust atoms? Because they make up everything.",
    "I asked my dog what two minus two is. He said nothing.",
    "Why did the scarecrow win an award? He was outstanding in his field.",
    "I only know 25 letters of the alphabet. I don't know why.",
    "What do you call a factory that makes okay products? A satisfactory.",
    "I told my wife she should embrace her mistakes. She gave me a hug.",
    "Why do we tell actors to 'break a leg'? Because every play has a "
    "cast.",
    "What's the best thing about Switzerland? I don't know, but the flag "
    "is a big plus.",
    "Did you hear about the mathematician who's afraid of negative "
    "numbers? He'll stop at nothing to avoid them.",
    "Why can't you give Elsa a balloon? Because she'll let it go.",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call a sleeping dinosaur? A dino-snore.",
    "I would tell you a construction joke, but I'm still working on it.",
    "Why did the bicycle fall over? Because it was two-tired.",
    "What did the ocean say to the beach? Nothing, it just waved.",
    "I'm on a seafood diet — I see food and I eat it.",
    "Why did the golfer bring extra socks? In case he got a hole in one.",
    "What do you call cheese that isn't yours? Nacho cheese.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "I bought some shoes from a drug dealer. I don't know what he laced "
    "them with, but I was tripping all day.",
)

# oracle-verbatim (general_content.json "quotes", complete, in order)
QUOTES: tuple[str, ...] = (
    '"The only way to do great work is to love what you do." — Steve Jobs',
    '"In the middle of difficulty lies opportunity." — Albert Einstein',
    '"It does not matter how slowly you go as long as you do not stop." '
    "— Confucius",
    "\"Life is what happens when you're busy making other plans.\" "
    "— John Lennon",
    '"The future belongs to those who believe in the beauty of their '
    'dreams." — Eleanor Roosevelt',
    '"Be yourself; everyone else is already taken." — Oscar Wilde',
    '"Two things are infinite: the universe and human stupidity; and '
    "I'm not sure about the universe.\" — Albert Einstein",
    "\"In three words I can sum up everything I've learned about life: "
    'it goes on." — Robert Frost',
    '"To be yourself in a world that is constantly trying to make you '
    'something else is the greatest accomplishment." — Ralph Waldo '
    "Emerson",
    '"It is never too late to be what you might have been." — George '
    "Eliot",
    '"You only live once, but if you do it right, once is enough." '
    "— Mae West",
    '"The way to get started is to quit talking and begin doing." '
    "— Walt Disney",
    '"If life were predictable it would cease to be life, and be without '
    'flavor." — Eleanor Roosevelt',
    "\"If you look at what you have in life, you'll always have more.\" "
    "— Oprah Winfrey",
    "\"If you set your goals ridiculously high and it's a failure, you "
    'will fail above everyone else\'s success." — James Cameron',
    '"Life is not measured by the number of breaths we take, but by the '
    'moments that take our breath away." — Maya Angelou',
    '"If you want to live a happy life, tie it to a goal, not to people '
    'or things." — Albert Einstein',
    '"Never let the fear of striking out keep you from playing the '
    'game." — Babe Ruth',
    "\"Money and success don't change people; they merely amplify what "
    'is already there." — Will Smith',
    '"Not how long, but how well you have lived is the main thing." '
    "— Seneca",
    '"The greatest glory in living lies not in never falling, but in '
    'rising every time we fall." — Nelson Mandela',
    '"The way I see it, if you want the rainbow, you gotta put up with '
    'the rain." — Dolly Parton',
    '"Do not go where the path may lead, go instead where there is no '
    'path and leave a trail." — Ralph Waldo Emerson',
    '"You will face many defeats in life, but never let yourself be '
    'defeated." — Maya Angelou',
    "\"Many of life's failures are people who did not realize how close "
    'they were to success when they gave up." — Thomas A. Edison',
)

# oracle-verbatim (general_content.json "trivia", complete, in order);
# entries carry the shipped ` || ` question/answer separator verbatim.
TRIVIA: tuple[str, ...] = (
    "What is the capital of Australia? || Canberra (not Sydney!)",
    "How many bones does a shark have? || Zero — sharks have no bones, "
    "only cartilage.",
    "What element does 'Au' represent on the periodic table? || Gold.",
    "How many sides does a heptagon have? || Seven.",
    "What is the fastest land animal? || The cheetah, reaching up to "
    "120 km/h.",
    "What is the largest planet in our solar system? || Jupiter.",
    "How many hearts does an octopus have? || Three.",
    "What language has the most words? || English, with over 170,000 "
    "words in current use.",
    "What is the smallest country in the world? || Vatican City.",
    "How many colors are in a rainbow? || Seven: red, orange, yellow, "
    "green, blue, indigo, and violet.",
    "What is the hardest natural substance on Earth? || Diamond.",
    "Which planet rotates backwards compared to most others? || Venus "
    "(and Uranus on its side).",
    "How many strings does a standard guitar have? || Six.",
    "What year did the Titanic sink? || 1912.",
    "What is the chemical formula for water? || H₂O.",
    "Which country invented the telephone? || Debated — Alexander Graham "
    "Bell was Scottish-born but patented it in the US.",
    "How many bones are in the adult human body? || 206.",
    "What is the longest river in the world? || The Nile (though some "
    "argue for the Amazon, depending on measurement).",
    "Which fruit is known as the 'king of fruits'? || Durian.",
    "What is the most common element in the universe? || Hydrogen.",
    "In what year did World War II end? || 1945.",
    "What is the speed of light (approximately)? || 299,792 km/s (about "
    "186,000 miles per second).",
    "How many teeth does an adult human have? || 32 (including wisdom "
    "teeth).",
    "What is the tallest mountain in the world? || Mount Everest "
    "(8,849 m).",
    "Which animal can change color to blend into its surroundings? || "
    "The chameleon (and several cephalopods like cuttlefish).",
)

# oracle-verbatim (general_cog.py module constants — never in the JSON)
GREETINGS: tuple[str, ...] = (
    "Hello!", "Hi there!", "Greetings!", "Hey!", "What's up?",
)

MOTIVATIONS: tuple[str, ...] = (
    "Believe in yourself and all that you are!",
    "Every expert was once a beginner. Keep going.",
    "You are capable of amazing things.",
    "Small steps every day lead to big results.",
    "Difficult roads often lead to beautiful destinations.",
)

# oracle-verbatim (general_cog.py 8-ball answers list)
EIGHTBALL: tuple[str, ...] = (
    "Yes!",
    "No.",
    "Maybe.",
    "Ask again later.",
    "It is certain.",
    "Definitely not.",
    "Signs point to yes.",
    "Don't count on it.",
)


def pick(pool: tuple[str, ...], label: str) -> str:
    """The shipped random-pick rule (general_cog.py, verbatim fallback)."""
    return random.choice(pool) if pool else f"No {label} available."
