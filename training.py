import os
import random
import threading
import urllib.request
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from treys import Card as TreysCard
except Exception:
    TreysCard = None

Card = TreysCard


class TrainingModule:
    def __init__(self, container, root=None):
        self.container = container
        self.root = root or container.winfo_toplevel()

        self.card_images = {}
        self.card_image_refs = {}
        self.avatar_images = {}
        self.card_back = None
        self.images_dir = os.path.join(os.path.dirname(__file__), "card_cache")
        os.makedirs(self.images_dir, exist_ok=True)

        sim_frame = ttk.LabelFrame(self.container, text="Simulation IA (3 bots)", padding=10)
        sim_frame.pack(fill="x", pady=(6, 10))

        ttk.Label(sim_frame, text="Nombre de parties :").grid(row=0, column=0, sticky="w")
        self.entry_sim_hands = ttk.Entry(sim_frame, width=10)
        self.entry_sim_hands.insert(0, "10000")
        self.entry_sim_hands.grid(row=0, column=1, sticky="w", padx=(4, 12))

        self.btn_simulate = ttk.Button(sim_frame, text="Lancer une simulation", command=self.start_ai_simulation)
        self.btn_simulate.grid(row=0, column=2, sticky="w")

        self.lbl_sim_status = tk.Label(sim_frame, text="Statut simulation : -", anchor="w")
        self.lbl_sim_status.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self.lbl_sim_b1 = tk.Label(sim_frame, text="Bot 1 : -", anchor="w")
        self.lbl_sim_b1.grid(row=2, column=0, columnspan=3, sticky="w")
        self.lbl_sim_b2 = tk.Label(sim_frame, text="Bot 2 : -", anchor="w")
        self.lbl_sim_b2.grid(row=3, column=0, columnspan=3, sticky="w")
        self.lbl_sim_b3 = tk.Label(sim_frame, text="Bot 3 : -", anchor="w")
        self.lbl_sim_b3.grid(row=4, column=0, columnspan=3, sticky="w")

        self.txt_sim_log = tk.Text(sim_frame, height=8)
        self.txt_sim_log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))

        graph_frame = ttk.LabelFrame(self.container, text="Graphes des bots", padding=10)
        graph_frame.pack(fill="x", pady=(0, 10))

        self.bot_graph_canvases = []
        for idx in range(3):
            bot_col = ttk.Frame(graph_frame)
            bot_col.grid(row=0, column=idx, padx=8, sticky="n")
            tk.Label(bot_col, text=f"Bot {idx + 1}", font=("Helvetica", 10, "bold")).pack(pady=(0, 4))
            canvas = tk.Canvas(bot_col, width=220, height=160, bg="white", highlightthickness=1, highlightbackground="#c0c0c0")
            canvas.pack()
            self.bot_graph_canvases.append(canvas)

        self._clear_bot_graphs()

        try:
            threading.Thread(target=self._prefetch_deck_images, daemon=True).start()
        except Exception:
            pass

    def start_ai_simulation(self):
        try:
            num_hands = int(self.entry_sim_hands.get().strip())
        except Exception:
            messagebox.showerror("Erreur", "Le nombre de parties doit etre un entier valide.")
            return

        if num_hands <= 0:
            messagebox.showerror("Erreur", "Le nombre de parties doit etre superieur a 0.")
            return

        self.btn_simulate.config(state="disabled")
        self.lbl_sim_status.config(text=f"Statut simulation : en cours ({num_hands} parties)")
        self.txt_sim_log.delete("1.0", "end")
        threading.Thread(target=self.run_ai_simulation, args=(num_hands,), daemon=True).start()

    def run_ai_simulation(self, num_hands):
        try:
            from treys import Deck, Evaluator
        except Exception:
            self.root.after(0, lambda: messagebox.showerror("Erreur", "La librairie 'treys' n'est pas installee."))
            self.root.after(0, lambda: self.btn_simulate.config(state="normal"))
            self.root.after(0, lambda: self.lbl_sim_status.config(text="Statut simulation : arrete"))
            return

        evaluator = Evaluator()
        wins = [0, 0, 0]
        ties = [0, 0, 0]
        ev_total = [0.0, 0.0, 0.0]

        def draw_many(deck, count):
            drawn = deck.draw(count)
            return drawn if isinstance(drawn, list) else [drawn]

        for _ in range(num_hands):
            deck = Deck()
            hands = [draw_many(deck, 2) for _ in range(3)]
            board = draw_many(deck, 5)

            scores = [evaluator.evaluate(board, hand) for hand in hands]
            best_score = min(scores)
            winners = [idx for idx, score in enumerate(scores) if score == best_score]

            pot = 3.0
            share = pot / len(winners)
            for idx in range(3):
                if idx in winners:
                    ev_total[idx] += share - 1.0
                    if len(winners) == 1:
                        wins[idx] += 1
                    else:
                        ties[idx] += 1
                else:
                    ev_total[idx] -= 1.0

        def equity(idx):
            return ((wins[idx] + ties[idx] / 3.0) / num_hands) * 100.0

        summary_lines = [
            f"Simulation terminee sur {num_hands} parties.",
            f"Bot 1 - Victoires: {wins[0]} | Egalites: {ties[0]} | Equite: {equity(0):.2f}% | EV moyen: {ev_total[0] / num_hands:.4f} jeton(s)/main",
            f"Bot 2 - Victoires: {wins[1]} | Egalites: {ties[1]} | Equite: {equity(1):.2f}% | EV moyen: {ev_total[1] / num_hands:.4f} jeton(s)/main",
            f"Bot 3 - Victoires: {wins[2]} | Egalites: {ties[2]} | Equite: {equity(2):.2f}% | EV moyen: {ev_total[2] / num_hands:.4f} jeton(s)/main",
        ]

        equities = [equity(i) for i in range(3)]
        ev_values = [ev_total[i] / num_hands for i in range(3)]

        def finalize():
            self.btn_simulate.config(state="normal")
            self.lbl_sim_status.config(text=f"Statut simulation : terminee ({num_hands} parties)")
            self.lbl_sim_b1.config(text=f"Bot 1 : Equite {equity(0):.2f}% | EV {ev_total[0] / num_hands:.4f} jeton(s)/main")
            self.lbl_sim_b2.config(text=f"Bot 2 : Equite {equity(1):.2f}% | EV {ev_total[1] / num_hands:.4f} jeton(s)/main")
            self.lbl_sim_b3.config(text=f"Bot 3 : Equite {equity(2):.2f}% | EV {ev_total[2] / num_hands:.4f} jeton(s)/main")
            self.txt_sim_log.insert("end", "\n".join(summary_lines) + "\n")
            self.txt_sim_log.see("end")
            self._render_bot_graphs(equities, ev_values)

        self.root.after(0, finalize)

    def _clear_bot_graphs(self):
        for canvas in getattr(self, "bot_graph_canvases", []):
            canvas.delete("all")
            canvas.create_text(110, 80, text="Lancez une simulation", fill="#666", font=("Helvetica", 10))

    def _render_bot_graphs(self, equities, ev_values):
        for idx, canvas in enumerate(self.bot_graph_canvases):
            self._draw_bot_graph(canvas, equities[idx], ev_values[idx], idx + 1)

    def _draw_bot_graph(self, canvas, equity_value, ev_value, bot_index):
        canvas.delete("all")

        width = int(canvas.cget("width"))
        height = int(canvas.cget("height"))
        margin_x = 22
        margin_y = 20
        chart_top = 24
        chart_bottom = height - 28
        chart_left = margin_x
        chart_right = width - margin_x
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top

        canvas.create_text(width // 2, 10, text=f"Bot {bot_index}", fill="#222", font=("Helvetica", 10, "bold"))
        canvas.create_line(chart_left, chart_bottom, chart_right, chart_bottom, fill="#333")
        canvas.create_line(chart_left, chart_bottom, chart_left, chart_top, fill="#333")

        max_equity = 100.0
        max_ev = max(1.0, abs(ev_value) * 1.4)

        bar_gap = 20
        bar_width = (chart_width - bar_gap) // 2 - 10
        bar1_x1 = chart_left + 15
        bar1_x2 = bar1_x1 + bar_width
        bar2_x1 = bar1_x2 + bar_gap
        bar2_x2 = bar2_x1 + bar_width

        equity_bar_h = int((equity_value / max_equity) * (chart_height - 10))
        ev_bar_h = int((abs(ev_value) / max_ev) * (chart_height - 10))

        bar1_y1 = chart_bottom - equity_bar_h
        bar2_y1 = chart_bottom - ev_bar_h

        equity_color = "#2e86de"
        ev_color = "#27ae60" if ev_value >= 0 else "#c0392b"

        canvas.create_rectangle(bar1_x1, bar1_y1, bar1_x2, chart_bottom, fill=equity_color, outline="")
        canvas.create_rectangle(bar2_x1, bar2_y1, bar2_x2, chart_bottom, fill=ev_color, outline="")

        canvas.create_text((bar1_x1 + bar1_x2) // 2, chart_bottom + 10, text="Equite", fill="#222", font=("Helvetica", 9))
        canvas.create_text((bar2_x1 + bar2_x2) // 2, chart_bottom + 10, text="EV", fill="#222", font=("Helvetica", 9))

        canvas.create_text((bar1_x1 + bar1_x2) // 2, max(bar1_y1 - 10, chart_top + 8), text=f"{equity_value:.1f}%", fill="#222", font=("Helvetica", 9, "bold"))
        canvas.create_text((bar2_x1 + bar2_x2) // 2, max(bar2_y1 - 10, chart_top + 8), text=f"{ev_value:.2f}", fill="#222", font=("Helvetica", 9, "bold"))

        canvas.create_text(width // 2, height - 10, text="Par main simulée", fill="#666", font=("Helvetica", 8))

    def _get_card_photo(self, card_str):
        s = str(card_str).strip().replace("[", "").replace("]", "").replace(",", "")
        if not s:
            return None

        if len(s) >= 2 and s[0].isdigit():
            rank = s[:-1]
            suit = s[-1]
        else:
            if len(s) < 2:
                return None
            rank = s[0]
            suit = s[1]

        rank = rank.upper()
        suit = suit.upper()
        rank_map = {"T": "0", "10": "0"}
        rank_code = rank_map.get(rank, rank)
        code = f"{rank_code}{suit}"

        if code in self.card_images:
            return self.card_images[code]

        local_path = os.path.join(self.images_dir, f"{code}.png")
        if not os.path.exists(local_path):
            url = f"https://deckofcardsapi.com/static/img/{code}.png"
            try:
                urllib.request.urlretrieve(url, local_path)
            except Exception:
                return None

        try:
            img = tk.PhotoImage(file=local_path)
            try:
                width = img.width()
                target = 72
                if width > target:
                    factor = max(1, int(width / target))
                    img = img.subsample(factor, factor)
            except Exception:
                pass

            self.card_images[code] = img
            return img
        except Exception:
            return None

    def _get_card_back(self):
        if self.card_back:
            return self.card_back

        local_path = os.path.join(self.images_dir, "back.png")
        if not os.path.exists(local_path):
            url = "https://deckofcardsapi.com/static/img/back.png"
            try:
                urllib.request.urlretrieve(url, local_path)
            except Exception:
                return None

        try:
            img = tk.PhotoImage(file=local_path)
            self.card_back = img
            return img
        except Exception:
            return None

    def _prefetch_deck_images(self):
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "0", "J", "Q", "K"]
        suits = ["S", "H", "D", "C"]

        for rank in ranks:
            for suit in suits:
                code = f"{rank}{suit}"
                local_path = os.path.join(self.images_dir, f"{code}.png")
                if not os.path.exists(local_path):
                    url = f"https://deckofcardsapi.com/static/img/{code}.png"
                    try:
                        urllib.request.urlretrieve(url, local_path)
                    except Exception:
                        pass

        back_path = os.path.join(self.images_dir, "back.png")
        if not os.path.exists(back_path):
            url = "https://deckofcardsapi.com/static/img/back.png"
            try:
                urllib.request.urlretrieve(url, back_path)
            except Exception:
                pass
