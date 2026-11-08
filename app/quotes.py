"""A local set of original study encouragement messages."""

import random
from collections import deque

_OPENINGS = (
    "Progress begins with the page in front of you.",
    "A focused minute is a useful place to start.",
    "Your attention is a skill you strengthen by returning.",
    "One clear problem can lead to a whole afternoon of progress.",
    "A slow, steady effort still moves the work forward.",
    "You do not need perfect conditions to make a good start.",
    "The next small decision can point you back to your goal.",
    "A difficult topic becomes friendlier one question at a time.",
    "Every time you refocus, you practise the habit you want.",
    "Your future understanding is built in moments like this.",
    "A short pause can become a calm return to meaningful work.",
    "The work in front of you deserves one honest attempt.",
    "Consistency is made from ordinary minutes used with care.",
    "You can make room for curiosity by setting distractions aside.",
    "A fresh page is waiting whenever you choose to begin again.",
    "Your pace is allowed to be thoughtful rather than hurried.",
    "One finished step is better than a perfect plan postponed.",
    "The effort you invest today gives tomorrow a stronger start.",
    "Attention grows when you gently bring it back.",
    "There is value in staying with one thing a little longer.",
)

_FOLLOWUPS = (
    "Give this moment your attention.",
    "Choose one next step and begin there.",
    "You only need to make the next minute count.",
    "Let curiosity guide your return.",
    "Take a breath, then continue at your own pace.",
    "Small progress is still real progress.",
    "Settle in and give the task a fair chance.",
    "Your effort matters more than a flawless start.",
    "Come back to the reason you chose this session.",
    "You can reset your focus without judging yourself.",
)

STUDY_QUOTES = tuple(
    f"{opening} {followup}"
    for opening in _OPENINGS
    for followup in _FOLLOWUPS
)


class QuoteSelector:
    def __init__(self, recent_count=12):
        self._recent = deque(maxlen=recent_count)

    def next_quote(self):
        available = [quote for quote in STUDY_QUOTES if quote not in self._recent]
        quote = random.choice(available or list(STUDY_QUOTES))
        self._recent.append(quote)
        return quote
