"""Seed Firestore with classic literature books and reading list items."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-d7d8c6f5a56e"

BOOKS = [
    {
        "id": "pride-and-prejudice",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "genre": "Victorian Romance / Satire of Manners",
        "pages": 432,
        "difficulty": "Intermediate",
        "themes": ["Class", "Marriage", "Pride & Prejudice", "Family"],
        "famous_quote": "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.",
        "synopsis": "The story follows the romantic conflicts of Elizabeth Bennet and Fitzwilliam Darcy as they overcome their respective pride and prejudices."
    },
    {
        "id": "crime-and-punishment",
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "year": 1866,
        "genre": "Russian Realism / Psychological Fiction",
        "pages": 671,
        "difficulty": "Advanced",
        "themes": ["Guilt", "Redemption", "Morality", "Alienation"],
        "famous_quote": "Pain and suffering are always inevitable for a large intelligence and a deep heart.",
        "synopsis": "The mental anguish and moral dilemmas of Rodion Raskolnikov, an impoverished ex-student in Saint Petersburg who plans to kill an unscrupulous pawnbroker."
    },
    {
        "id": "frankenstein",
        "title": "Frankenstein; or, The Modern Prometheus",
        "author": "Mary Shelley",
        "year": 1818,
        "genre": "Gothic Horror / Science Fiction",
        "pages": 280,
        "difficulty": "Intermediate",
        "themes": ["Hubris", "Isolation", "Creation & Responsibility", "Monstrosity"],
        "famous_quote": "Beware; for I am fearless, and therefore powerful.",
        "synopsis": "Scientist Victor Frankenstein creates a sentient creature in an unorthodox scientific experiment, only to abandon it, triggering tragic consequences."
    },
    {
        "id": "the-odyssey",
        "title": "The Odyssey",
        "author": "Homer",
        "year": -800,
        "genre": "Ancient Epic Poetry",
        "pages": 541,
        "difficulty": "Advanced",
        "themes": ["Homecoming (Nostos)", "Hospitality (Xenia)", "Fate & Free Will", "Heroism"],
        "famous_quote": "Of all creatures that breathe and move upon the earth, nothing is bred that is weaker than man.",
        "synopsis": "The ten-year journey of Odysseus, king of Ithaca, trying to return home after the fall of Troy while facing mythical monsters and divine wrath."
    },
    {
        "id": "the-great-gatsby",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "genre": "Modernist / Jazz Age Tragedy",
        "pages": 180,
        "difficulty": "Accessible",
        "themes": ["The American Dream", "Wealth & Decay", "Obsession", "Memory"],
        "famous_quote": "So we beat on, boats against the current, borne back ceaselessly into the past.",
        "synopsis": "Narrator Nick Carraway is drawn into the lavish world of his enigmatic neighbor Jay Gatsby and Gatsby's obsessive love for Daisy Buchanan."
    },
    {
        "id": "1984",
        "title": "1984",
        "author": "George Orwell",
        "year": 1949,
        "genre": "Dystopian Political Fiction",
        "pages": 328,
        "difficulty": "Intermediate",
        "themes": ["Totalitarianism", "Surveillance", "Truth & Language", "Rebellion"],
        "famous_quote": "War is peace. Freedom is slavery. Ignorance is strength.",
        "synopsis": "In a totalitarian future under the watchful eye of Big Brother, Winston Smith dares to rebel through secret diary writing and forbidden love."
    }
]

def seed():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    
    # Seed classics collection
    books_ref = db.collection("classic_books")
    for book in BOOKS:
        doc_id = book["id"]
        books_ref.document(doc_id).set(book)
        print(f"  ✓ Seeded book: {book['title']} ({doc_id})")
        
    print("\n✅ Firestore successfully seeded!")

if __name__ == "__main__":
    seed()
