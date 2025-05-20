import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from collections import Counter
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
from bs4 import BeautifulSoup

# === Load full card data from a Scryfall-style JSON ===
def load_card_database(path="cards_sample.json"):
    if not os.path.exists(path):
        raise FileNotFoundError("Card database not found.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)

# === Parse Player.log to extract owned card names ===
def parse_mtga_collection(log_path):
    if not os.path.exists(log_path):
        messagebox.showerror("File Error", "MTGA Player.log not found.")
        return []

    print("Reading log file:", log_path)
    owned_cards = []
    found_data = False

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if 'GetPlayerCardsV3' in line:
                    try:
                        json_str = "".join(lines[i+1:i+50])  # scan ahead for up to 50 lines
                        json_blob = json.loads(json_str)
                        cards = json_blob.get("cards", [])
                        if cards:
                            found_data = True
                        for card in cards:
                            amount = card.get("amount", 0)
                            name = card.get("name", "").replace("’", "'").strip()
                            if amount > 0:
                                owned_cards.extend([name] * amount)
                        break
                    except json.JSONDecodeError as e:
                        print("JSON decode error:", e)
                    except Exception as e:
                        print("Error parsing line:", e)
    except Exception as e:
        print("Failed to open or read log:", e)
        return []

    if not found_data:
        print("⚠️  No 'GetPlayerCardsV3' data block found. Log may be truncated or outdated.")
    print("✅ Total cards parsed from log:", len(owned_cards))
    print("🃏 Sample owned cards:", owned_cards[:10])
    return owned_cards

# === Helper functions to retrieve selected values ===
color_reverse_map = {"White": "W", "Blue": "U", "Black": "B", "Red": "R", "Green": "G", "Colorless": "C"}

def get_selected_colors():
    return [color_reverse_map[color] for color, var in color_vars.items() if var.get() == 1]

def get_selected_keywords():
    return [kw for kw, var in keyword_vars.items() if var.get() == 1]

# === Build Deck with Color and Format Filtering ===
def build_deck(card_pool, owned_cards, selected_keywords, selected_colors, selected_format):
    print("\n=== Deck Build Debug Info ===")
    print("Selected Keywords:", selected_keywords)
    print("Selected Colors:", selected_colors)
    print("Owned Cards Sample:", owned_cards[:10])

    suggested_cards = []
    filtered = card_pool.copy()
    print("Initial pool size:", len(filtered))

    if selected_keywords:
        filtered = filtered[filtered['keywords'].apply(lambda kws: any(kw.lower() in [k.lower() for k in kws] for kw in selected_keywords))]
    if selected_colors:
        filtered = filtered[filtered['color'].isin(selected_colors)]
    if selected_format != "Any":
        filtered = filtered[filtered['format'].str.contains(selected_format)]

    print("Filtered pool size after color/keyword/format:", len(filtered))
    filtered = filtered.sort_values(by="type")

    deck = []
    suggested_cards = []
    card_counts = Counter()
    owned_names = set(owned_cards)

    for card in filtered.itertuples():
        synergy = sum(1 for kw in selected_keywords if kw.lower() in [k.lower() for k in card.keywords])
        count = min(4, max(1, synergy))

        if card.name in owned_names:
            owned_count = owned_cards.count(card.name)
            final_count = min(count, owned_count, 4)
            card_counts[card.name] += final_count
        else:
            card_counts[card.name] += count
            suggested_cards.append((card.name, count))

        if sum(card_counts.values()) >= 36:
            break

    deck = []
    for name, count in card_counts.items():
        deck.extend([name] * count)

    colors = filtered[filtered['name'].isin(deck)]["color"].value_counts().to_dict()
    total_color_cards = sum(colors.values())
    if total_color_cards > 0:
        for color, count in colors.items():
            land_name = "Forest" if color == "Green" else "Mountain" if color == "Red" else "Plains" if color == "White" else "Island" if color == "Blue" else "Swamp"
            land_amount = round((count / total_color_cards) * (60 - len(deck)))
            deck.extend([land_name] * land_amount)

    return deck[:60], suggested_cards

# Other functions remain unchanged...

def plot_mana_curve(deck, card_db):
    mana_costs = []
    for card in deck:
        base_name = card.replace(" (wildcard)", "")
        match = card_db[card_db['name'] == base_name]
        if not match.empty:
            mana_costs.append(match.iloc[0].get("cmc", 0))

    fig, ax = plt.subplots()
    ax.hist(mana_costs, bins=range(0, int(max(mana_costs + [1])) + 1), align='left', rwidth=0.8)
    ax.set_title("Mana Curve")
    ax.set_xlabel("Converted Mana Cost")
    ax.set_ylabel("Card Count")
    return fig

def plot_card_types(deck, card_db):
    type_counter = Counter()
    for card in deck:
        base_name = card.replace(" (wildcard)", "")
        match = card_db[card_db['name'] == base_name]
        if not match.empty:
            type_counter[match.iloc[0].get("type", "Unknown")] += 1

    labels = list(type_counter.keys())
    sizes = list(type_counter.values())

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.set_title("Card Type Distribution")
    return fig

# === Fetch Meta Decks (Basic Example from MTGMeta.io) ===



# === Initialize UI Root and Exit Handler ===
root = tk.Tk()
root.title("MTGA Deck Builder")

# === Set up UI components ===
frame = ttk.Frame(root, padding=10)
frame.grid(row=0, column=0, sticky="nsew")

keywords = ["burn", "damage", "haste", "ramp", "lifelink", "sacrifice", "landfall"]
keyword_vars = {}
ttk.Label(frame, text="Select Desired Synergies / Archetypes:").grid(row=0, column=0, columnspan=2, sticky="w")
for i, kw in enumerate(keywords):
    var = tk.IntVar()
    chk = ttk.Checkbutton(frame, text=kw.capitalize(), variable=var)
    chk.grid(row=(i // 2) + 1, column=(i % 2), sticky="w")
    keyword_vars[kw] = var

color_vars = {}
colors = ["Red", "Green", "Blue", "White", "Black"]
ttk.Label(frame, text="Preferred Colors:").grid(row=5, column=0, columnspan=2, sticky="w")
for i, color in enumerate(colors):
    var = tk.IntVar()
    chk = ttk.Checkbutton(frame, text=color, variable=var)
    chk.grid(row=6 + (i // 2), column=(i % 2), sticky="w")
    color_vars[color] = var

format_var = tk.StringVar()
ttk.Label(frame, text="Game Format:").grid(row=8, column=0, sticky="w")
format_dropdown = ttk.Combobox(frame, textvariable=format_var, values=["Any", "Standard", "Historic", "Alchemy", "Explorer"])
format_dropdown.grid(row=8, column=1, sticky="w")
format_dropdown.current(0)

log_path = tk.StringVar()
ttk.Label(frame, text="MTGA Player.log path:").grid(row=9, column=0, sticky="w")
ttk.Entry(frame, textvariable=log_path, width=40).grid(row=10, column=0, sticky="w")
def browse_log():
    path = filedialog.askopenfilename(title="Select MTGA Player.log")
    if path:
        log_path.set(path)

browse_btn = ttk.Button(frame, text="Browse", command=browse_log)
browse_btn.grid(row=10, column=1, sticky="w")

ttk.Button(frame, text="Build Deck", command=lambda: build_deck_from_ui()).grid(row=11, column=0, pady=10)
ttk.Button(frame, text="Export Deck", command=lambda: export_deck()).grid(row=11, column=1, pady=10)

output = tk.Text(frame, height=10, width=60)
output.grid(row=12, column=0, columnspan=2, pady=5)

chart_frame = ttk.Frame(root, padding=10)
chart_frame.grid(row=1, column=0, sticky="nsew")

def build_deck_from_ui():
    selected_keywords = get_selected_keywords()
    selected_colors = get_selected_colors()


    selected_format = format_var.get()

    if not selected_keywords:
        messagebox.showwarning("No Keywords Selected", "Please select at least one keyword/archetype.")
        return

    try:
        card_db = load_card_database()
        
        owned = parse_mtga_collection(log_path.get())
        # Since we are not using owned cards, treat all filtered cards as suggestions
        deck, suggested_cards = build_deck(card_db, owned, selected_keywords, selected_colors, selected_format)

        output.delete(1.0, tk.END)
        card_counts = Counter(deck)
        for card, count in card_counts.items():
            output.insert(tk.END, f"{count}x {card}\n")

        if suggested_cards:
            output.insert(tk.END, "\nSuggested (Not Owned):\n")
            for name, count in suggested_cards:
                output.insert(tk.END, f"{count}x {name}")


    except Exception as e:
        messagebox.showerror("Error", str(e))
        return

    for widget in chart_frame.winfo_children():
        widget.destroy()

    fig1 = plot_mana_curve(deck, card_db)
    canvas1 = FigureCanvasTkAgg(fig1, master=chart_frame)
    canvas1.draw()
    canvas1.get_tk_widget().pack()

    fig2 = plot_card_types(deck, card_db)
    canvas2 = FigureCanvasTkAgg(fig2, master=chart_frame)
    canvas2.draw()
    canvas2.get_tk_widget().pack()

def export_deck():
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
    if file_path:
        try:
            content = output.get("1.0", tk.END)
            with open(file_path, "w") as f:
                f.write(content)
            messagebox.showinfo("Export Successful", f"Deck exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

def on_closing():
    plt.close('all')
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# === Begin Mainloop to Display UI ===
root.mainloop()




def fetch_meta_decks():
    import time
    import logging
    from bs4 import BeautifulSoup

    cache_file = "meta_decks_cache.json"

    # Check if cached version exists
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                if time.time() - cached_data.get("timestamp", 0) < 86400:  # 1 day cache
                    return cached_data.get("decks", [])
        except Exception as e:
            logging.warning(f"Failed to load cache: {e}")

    sources = [
        "https://mtgmeta.io/api/topdecks",
        "https://mtgmeta.io/api/archetypes"
    ]

    for url in sources:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200 or not response.content.strip():
                logging.warning(f"Empty or bad response from {url}")
                continue

            data = response.json()
            if "data" in data:
                decks = [deck.get("deck", "Unknown Deck") for deck in data.get("data", []) if "deck" in deck]
                if decks:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump({"timestamp": time.time(), "decks": decks[:5]}, f)
                    return decks[:5]

        except Exception as e:
            logging.error(f"Error fetching from {url}: {e}")
            continue

    # Try scraping from MTGGoldfish as a fallback
    try:
        response = requests.get("https://www.mtggoldfish.com/metagame/standard/full", timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        deck_elements = soup.select(".metagame-tiers-container .deck-price-box h2 a")
        decks = [deck.text.strip() for deck in deck_elements[:5]]

        if decks:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"timestamp": time.time(), "decks": decks}, f)
            return decks
    except Exception as e:
        logging.error(f"Failed to scrape fallback source: {e}")

    messagebox.showwarning("Meta Deck Error", "Unable to fetch meta decks from any source.\nCheck your internet connection, firewall settings, or try again later.")
    return []


