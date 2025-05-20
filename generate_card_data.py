import json
import requests

# Download the full Scryfall card database from the specified URL
SCRYFALL_URL = "https://data.scryfall.io/all-cards/all-cards-20250520092301.json"
OUTPUT_FILE = "cards_sample.json"

def generate_card_data():
    print("Downloading card data from Scryfall...")
    response = requests.get(SCRYFALL_URL)
    if response.status_code != 200:
        raise Exception("Failed to download card data from Scryfall.")

    full_data = response.json()
    processed_cards = []
    seen_names = set()

    for card in full_data:
        if card.get("layout") != "normal":
            continue
        name = card["name"]
        if name in seen_names:
            continue
        seen_names.add(name)
        processed_cards.append({
            "name": name,
            "type": card["type_line"].split(" — ")[0],
            "color": card["colors"][0] if card["colors"] else "Colorless",
            "keywords": [kw.lower() for kw in card.get("keywords", [])],
            "cmc": card["cmc"],
            "format": ",".join(fmt for fmt, status in card["legalities"].items() if status == "legal")
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(processed_cards, f, indent=2)

    print(f"Successfully saved {len(processed_cards)} cards to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_card_data()
