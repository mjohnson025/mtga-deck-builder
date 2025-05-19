import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from collections import Counter
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests

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

    owned_cards = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if 'GetPlayerCardsV3' in line:
                try:
                    json_data = json.loads(line[line.index('{'):])
                    for card in json_data.get("cards", []):
                        if card.get("amount", 0) > 0:
                            owned_cards.extend([card["name"]] * card["amount"])
                except:
                    continue
    return owned_cards

# === Build Deck with Color and Format Filtering ===
def build_deck(card_pool, owned_cards, selected_keywords, selected_colors, selected_format):
    filtered = card_pool.copy()

    if selected_keywords:
        filtered = filtered[filtered['keywords'].apply(lambda kws: any(kw in kws for kw in selected_keywords))]
    if selected_colors:
        filtered = filtered[filtered['color'].isin(selected_colors)]
    if selected_format != "Any":
        filtered = filtered[filtered['format'].str.contains(selected_format)]

    filtered = filtered[filtered['name'].isin(owned_cards)]
    filtered = filtered.sort_values(by="type")

    deck = []
    for card in filtered.itertuples():
        count = min(4, owned_cards.count(card.name))
        deck.extend([card.name] * count)
        if len(deck) >= 40:
            break

    colors = filtered["color"].value_counts().to_dict()
    total_color_cards = sum(colors.values())
    for color, count in colors.items():
        land_name = "Forest" if color == "Green" else "Mountain" if color == "Red" else "Plains" if color == "White" else "Island" if color == "Blue" else "Swamp"
        deck.extend([land_name] * round((count / total_color_cards) * (60 - len(deck))))

    return deck[:60]

# === Fetch Meta Decks (Basic Example from MTGMeta.io) ===
def fetch_meta_decks():
    try:
        response = requests.get("https://mtgmeta.io/api/topdecks")
        if response.status_code == 200:
            data = response.json()
            decks = [deck["deck"] for deck in data.get("data", [])]
            return decks[:5]  # return top 5 decks
        return []
    except Exception as e:
        messagebox.showerror("Meta Deck Error", str(e))
        return []

# === Visualize Mana Curve ===
def plot_mana_curve(deck, card_db):
    mana_costs = []
    types = []
    for card in deck:
        match = card_db[card_db['name'] == card]
        if not match.empty:
            mana_costs.append(match.iloc[0].get("cmc", 0))
            types.append(match.iloc[0].get("type", "Unknown"))

    fig, ax = plt.subplots()
    ax.hist(mana_costs, bins=range(0, max(mana_costs + [1]) + 1), align='left', rwidth=0.8)
    ax.set_title("Mana Curve")
    ax.set_xlabel("Converted Mana Cost")
    ax.set_ylabel("Card Count")
    return fig

# === Visualize Card Type Breakdown ===
def plot_card_types(deck, card_db):
    type_counter = Counter()
    for card in deck:
        match = card_db[card_db['name'] == card]
        if not match.empty:
            type_counter[match.iloc[0].get("type", "Unknown")] += 1

    labels = list(type_counter.keys())
    sizes = list(type_counter.values())

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.set_title("Card Type Distribution")
    return fig

# === Export deck to file ===
def export_deck(deck):
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
    if file_path:
        with open(file_path, "w") as f:
            card_counts = Counter(deck)
            for card, count in card_counts.items():
                f.write(f"{count} {card}\n")
        messagebox.showinfo("Export Successful", f"Deck exported to {file_path}")

# === UI Actions ===
def generate_deck():
    selected_keywords = [kw for kw, var in keyword_vars.items() if var.get() == 1]
    selected_colors = [color for color, var in color_vars.items() if var.get() == 1]
    selected_format = format_var.get()

    if not selected_keywords:
        messagebox.showwarning("No Keywords Selected", "Please select at least one keyword/archetype.")
        return
    try:
        owned = parse_mtga_collection(log_path.get())
        global deck
        deck = build_deck(card_db, owned, selected_keywords, selected_colors, selected_format)
        output.delete(1.0, tk.END)
        card_counts = Counter(deck)
        for card, count in card_counts.items():
            output.insert(tk.END, f"{count}x {card}\n")

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

        # Meta Deck Preview (future: comparison logic)
        meta_decks = fetch_meta_decks()
        if meta_decks:
            output.insert(tk.END, f"\n\nTop Meta Deck Samples:\n")
            for decklist in meta_decks:
                output.insert(tk.END, f"- {decklist}\n")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# === File Browser for Player.log ===
def browse_log():
    path = filedialog.askopenfilename(title="Select MTGA Player.log")
    if path:
        log_path.set(path)

# === Setup UI ===
root = tk.Tk()
root.title("MTGA Deck Builder")

frame = ttk.Frame(root, padding=10)
frame.grid(row=0, column=0, sticky="nsew")

keywords = ["burn", "damage", "haste", "ramp", "lifegain", "sacrifice", "landfall"]
keyword_vars = {}
card_db = load_card_database()
log_path = tk.StringVar()

# Keywords Section
ttk.Label(frame, text="Select Desired Synergies / Archetypes:").grid(row=0, column=0, columnspan=2, sticky="w")
for i, kw in enumerate(keywords):
    var = tk.IntVar()
    chk = ttk.Checkbutton(frame, text=kw.capitalize(), variable=var)
    chk.grid(row=(i // 2) + 1, column=(i % 2), sticky="w")
    keyword_vars[kw] = var

# Color Preference Section
color_vars = {}
colors = ["Red", "Green", "Blue", "White", "Black"]
ttk.Label(frame, text="Preferred Colors:").grid(row=4, column=0, columnspan=2, sticky="w")
for i, color in enumerate(colors):
    var = tk.IntVar()
    chk = ttk.Checkbutton(frame, text=color, variable=var)
    chk.grid(row=5 + (i // 2), column=(i % 2), sticky="w")
    color_vars[color] = var

# Format Dropdown
ttk.Label(frame, text="Game Format:").grid(row=7, column=0, sticky="w")
format_var = tk.StringVar()
format_dropdown = ttk.Combobox(frame, textvariable=format_var, values=["Any", "Standard", "Historic", "Alchemy", "Explorer"])
format_dropdown.grid(row=7, column=1, sticky="w")
format_dropdown.current(0)

# Log path input and browse button
ttk.Label(frame, text="MTGA Player.log path:").grid(row=8, column=0, sticky="w")
ttk.Entry(frame, textvariable=log_path, width=40).grid(row=9, column=0, sticky="w")
ttk.Button(frame, text="Browse", command=browse_log).grid(row=9, column=1, sticky="w")

# Build and Export Buttons
ttk.Button(frame, text="Build Deck", command=generate_deck).grid(row=10, column=0, pady=10)
ttk.Button(frame, text="Export Deck", command=lambda: export_deck(deck)).grid(row=10, column=1, pady=10)

output = tk.Text(frame, height=10, width=60)
output.grid(row=11, column=0, columnspan=2, pady=5)

chart_frame = ttk.Frame(root, padding=10)
chart_frame.grid(row=1, column=0, sticky="nsew")

root.mainloop()

