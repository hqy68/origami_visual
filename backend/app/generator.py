"""Turn a subject ("swan", a photo of a koi) into a crease pattern and steps.

Designing a new crease pattern for any shape (circle packing, the tree method) is a
research problem that TreeMaker-style tools solve with heavy optimisation. This
generator takes the practical route: work out the subject's body plan (which flaps
it needs), pick the traditional base whose flaps match, map body parts to the corners
of the crease pattern, and add shaping steps for that category. Results are labelled
as a starting point, and catalog matches of real designs are shown next to them.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .bases import get_base


class BodyPlan(BaseModel):
    subject: str
    category: str = Field(description="bird | fish | quadruped | flower | insect | container | plane | geometric | other")
    appendages: List[str] = Field(default_factory=list, description="flap-needing parts, e.g. head, tail, wing, leg")
    search_terms: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    source: str = "keywords"


CATEGORY_WORDS: Dict[str, List[str]] = {
    "bird": ["bird", "crane", "swan", "dove", "owl", "parrot", "eagle", "penguin", "flamingo",
             "hummingbird", "duck", "goose", "chicken", "rooster", "peacock", "turkey", "pigeon"],
    "fish": ["fish", "koi", "goldfish", "shark", "whale", "dolphin", "angelfish", "seal", "ray"],
    "quadruped": ["dog", "cat", "fox", "wolf", "horse", "deer", "elephant", "lion", "tiger", "bear",
                  "rabbit", "bunny", "mouse", "pig", "cow", "giraffe", "frog", "turtle", "lizard",
                  "dragon", "dinosaur", "hedgehog", "squirrel"],
    "flower": ["flower", "tulip", "rose", "lily", "lotus", "iris", "daisy", "blossom", "sunflower", "leaf"],
    "insect": ["insect", "beetle", "butterfly", "spider", "scorpion", "mantis", "ant", "bee",
               "cicada", "dragonfly", "crab", "lobster", "bug"],
    "container": ["box", "cup", "bowl", "tray", "container", "envelope", "wallet", "basket", "masu"],
    "plane": ["plane", "airplane", "jet", "glider", "dart", "rocket", "boat", "ship"],
    "geometric": ["star", "cube", "kusudama", "ball", "ornament", "heart", "diamond", "shuriken"],
}

DEFAULT_APPENDAGES = {
    "bird": ["head/neck", "tail", "left wing", "right wing"],
    "fish": ["head", "tail", "top fin", "bottom fin"],
    "quadruped": ["head", "tail", "front legs", "back legs"],
    "flower": ["petal", "petal", "petal", "petal"],
    "insect": ["head", "abdomen", "legs (pair)", "legs (pair)"],
    "container": [],
    "plane": ["nose"],
    "geometric": [],
    "other": ["main point"],
}

BASE_FOR = {
    "bird": "bird", "fish": "fish", "quadruped": "bird", "flower": "preliminary",
    "insect": "bird", "container": "blintz", "plane": "kite", "geometric": "waterbomb",
    "other": "kite",
}

# Which corner of the crease pattern becomes which flap, per base.
CORNERS = {
    "bird": [(0, 1), (1, 0), (0, 0), (1, 1)],      # two legs, then the two petals
    "fish": [(0, 0), (1, 1), (1, 0), (0, 1)],      # two long points, then two fins
    "kite": [(0, 0)],
    "preliminary": [(0, 0), (1, 0), (1, 1), (0, 1)],
    "waterbomb": [(0, 0), (1, 0), (1, 1), (0, 1)],
    "blintz": [],
}

SHAPING: Dict[str, List[str]] = {
    "bird": [
        "Fold the lower edges of the two bottom flaps to the centre line on both sides "
        "to make them thin.",
        "Inside-reverse-fold one thin flap up to make the {0}, and the other to make "
        "the {1}.",
        "Inside-reverse-fold the tip of the {0} flap to form the head or beak.",
        "Fold the two upper flaps down to become the {2} and {3}; gently pull them apart "
        "to shape the body.",
    ],
    "fish": [
        "Fold the short fins out to the sides: these become the {2} and {3}.",
        "Fold the long point at one end back on itself to shape the {0}.",
        "Make a crimp near the other long point to angle the {1}.",
        "Round the body by softly curving the centre crease.",
    ],
    "quadruped": [
        "Narrow all four flaps by folding their edges to the centre line.",
        "Inside-reverse-fold one bottom flap forward and up for the {0}; reverse-fold "
        "its tip down to make the snout.",
        "Inside-reverse-fold the opposite bottom flap back for the {1}.",
        "Fold the two upper flaps down at an angle on each side for the {2} and {3}; "
        "crimp at the joints to make them stand.",
    ],
    "flower": [
        "With the open end up, fold the lower edges of each flap to the centre line "
        "(kite folds) on all four sides.",
        "Fold the top points down and curl each {0} outward around a pencil.",
        "Pinch the closed bottom point to form the stem end, or blow gently into the "
        "small hole to puff the blossom.",
    ],
    "insect": [
        "Insects need many thin flaps. Narrow each of the four flaps by folding "
        "edges to the centre, twice if needed.",
        "Use the top flap as the {0} and the bottom flap as the {1}.",
        "Split each side flap lengthwise with a reverse fold to get the {2} and {3}.",
    ],
    "container": [
        "Fold the outer edges of the blintzed square to the centre, unfold, and repeat "
        "the other way to make a grid of creases.",
        "Open two opposite corners, raise the sides along the creases, and fold the "
        "remaining corners up and over the walls to lock the box.",
    ],
    "plane": [
        "Fold the kite in half along the centre line so the folds are outside.",
        "Fold each side down to form wings, leaving a narrow keel at the {0} end.",
        "Bend the wing tips up slightly for stability.",
    ],
    "geometric": [
        "Geometric shapes are usually modular: fold several identical units from "
        "this base and slot them together. See the matching tutorials for a unit design.",
    ],
    "other": [
        "Use the long point as the {0}; narrow it by folding edges to the centre line.",
        "Shape the rest of the form with reverse folds and crimps to match your subject.",
    ],
}

LIMITS = {
    "quadruped": "A four-legged animal with a head and tail needs six flaps; classic bases "
                 "give four or five. For more flaps, blintz the square first (fold the "
                 "corners to the centre) and then fold a bird base from it.",
    "insect": "Realistic insects use box-pleated or tree-method designs with many more "
              "flaps than any traditional base. The catalog matches are the better guide.",
    "geometric": "Most geometric forms are modular or tessellations, not one-sheet bases.",
}


def keyword_plan(query: str) -> BodyPlan:
    words = query.lower().split()
    category = "other"
    for cat, vocab in CATEGORY_WORDS.items():
        if any(w.strip(".,!?s") in vocab or w.strip(".,!?") in vocab for w in words):
            category = cat
            break
    return BodyPlan(subject=query.strip() or "model", category=category,
                    appendages=list(DEFAULT_APPENDAGES[category]),
                    search_terms=[query])


def generate(plan: BodyPlan) -> dict:
    category = plan.category if plan.category in BASE_FOR else "other"
    base_id = BASE_FOR[category]
    base = get_base(base_id)
    parts = list(plan.appendages) or list(DEFAULT_APPENDAGES[category])
    corners = CORNERS[base_id]
    padded = (parts + list(DEFAULT_APPENDAGES[category]) + ["extra flap"] * 4)[:max(4, len(corners))]
    labels = [{"corner": list(c), "part": p} for c, p in zip(corners, padded)]
    shaping = [s.format(*padded) for s in SHAPING[category]]
    notes = [n for n in (LIMITS.get(category), plan.notes) if n]
    if len(parts) > base["flaps"]:
        notes.append(f"{plan.subject} needs about {len(parts)} flaps but the {base['title'].lower()} "
                     f"gives {base['flaps']}; some parts will have to share a flap.")
    return {
        "subject": plan.subject,
        "category": category,
        "body_plan_source": plan.source,
        "base": base,
        "flap_labels": labels,
        "steps": [{"phase": "base", "text": t} for t in base["steps"]]
                 + [{"phase": "shaping", "text": t} for t in shaping],
        "notes": notes,
        "disclaimer": "Generated from a traditional base. The crease pattern is checked for "
                      "local flat-foldability; the shaping steps are a template, not a tested "
                      "design. For a finished model, use one of the catalog matches.",
    }
