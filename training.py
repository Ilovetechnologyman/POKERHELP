import threading
import random
import os
import urllib.request
from tkinter import messagebox, ttk
import tkinter as tk

# Try to import treys Card at module level so UI callbacks can use it
try:
    from treys import Card as TreysCard
except Exception:
    TreysCard = None

# Make a module-level Card name pointing to TreysCard so UI callbacks can use it
Card = TreysCard


class TrainingModule:
    def __init__(self, container, root=None):
        # container is the frame/tab where UI widgets will be placed
        # root is the main Tk root (used for messagebox and .after)
        self.container = container
        self.root = root or container.winfo_toplevel()
        self.training_running = False

        # Training options (Start in BB, SB, BB)
        opts_frame = ttk.Frame(self.container)
        opts_frame.pack(fill="x", pady=(6, 4))

        ttk.Label(opts_frame, text="Start (blinds) :").grid(row=0, column=0, sticky="w")
        self.entry_start_blinds = ttk.Entry(opts_frame, width=8)
        self.entry_start_blinds.insert(0, "25")
        self.entry_start_blinds.grid(row=0, column=1, sticky="w", padx=(4, 12))

        ttk.Label(opts_frame, text="SB :").grid(row=0, column=2, sticky="w")
        self.entry_sb = ttk.Entry(opts_frame, width=6)
        self.entry_sb.insert(0, "0.5")
        self.entry_sb.grid(row=0, column=3, sticky="w", padx=(4, 12))

        ttk.Label(opts_frame, text="BB :").grid(row=0, column=4, sticky="w")
        self.entry_bb = ttk.Entry(opts_frame, width=6)
        self.entry_bb.insert(0, "1")
        self.entry_bb.grid(row=0, column=5, sticky="w", padx=(4, 0))

        # Start/stop training button
        self.btn_train = ttk.Button(self.container, text="Demarrer entrainement", command=self.toggle_training)
        self.btn_train.pack(pady=(6, 6), fill="x")

        self.frame_training = ttk.LabelFrame(self.container, text="Mode Entrainement (1v1v1)", padding=10)
        self.frame_training.pack(fill="x", pady=(0, 10))

        self.lbl_train_status = tk.Label(self.frame_training, text="Statut : arrete", anchor="w")
        self.lbl_train_status.pack(fill="x")
        self.lbl_train_roles = tk.Label(self.frame_training, text="Positions : -", anchor="w")
        self.lbl_train_roles.pack(fill="x")
        self.lbl_train_hand = tk.Label(self.frame_training, text="Main (vous) : -", anchor="w")
        self.lbl_train_hand.pack(fill="x")
        self.lbl_train_win = tk.Label(self.frame_training, text="Win% estime : -", anchor="w")
        self.lbl_train_win.pack(fill="x")

        self.txt_train_log = tk.Text(self.frame_training, height=6)
        self.txt_train_log.pack(fill="x", pady=(6, 0))

        # User action area
        actions_frame = ttk.Frame(self.frame_training)
        actions_frame.pack(fill="x", pady=(6, 0))

        self.btn_raise = ttk.Button(actions_frame, text="Relancer (Raise)", command=self.on_raise)
        self.btn_raise.pack(side="left", expand=True, fill="x", padx=4)
        self.btn_call = ttk.Button(actions_frame, text="Suivre/Check (Call/Check)", command=self.on_call)
        self.btn_call.pack(side="left", expand=True, fill="x", padx=4)
        self.btn_fold = ttk.Button(actions_frame, text="Se coucher (Fold)", command=self.on_fold)
        self.btn_fold.pack(side="left", expand=True, fill="x", padx=4)

        # State for waiting user action
        self.wait_for_action = None
        self.selected_action = None
        self.current_round = None

        # Pot / stacks / community cards
        info_frame = ttk.Frame(self.container)
        info_frame.pack(fill="x", pady=(6, 4))

        self.lbl_pot = ttk.Label(info_frame, text="Pot: 0", font=(None, 10, "bold"))
        self.lbl_pot.pack(side="left", padx=6)

        self.lbl_stacks = ttk.Label(info_frame, text="Stacks - Vous: - | Opp1: - | Opp2: -")
        self.lbl_stacks.pack(side="left", padx=10)

        # Community cards display
        self.community_frame = ttk.Frame(self.container)
        self.community_frame.pack(fill="x", pady=(6, 4))
        self.community_cards_frame = tk.Frame(self.community_frame)
        self.community_cards_frame.pack(fill="x")

        # Opponents display (avatars + card backs)
        self.opponents_frame = ttk.Frame(self.container)
        self.opponents_frame.pack(fill="x", pady=(6, 4))

        # Opponent 1
        self.opp1_frame = ttk.Frame(self.opponents_frame)
        self.opp1_frame.pack(side="left", padx=10)
        self.opp1_avatar = tk.Label(self.opp1_frame, text="O1", width=6, height=3, relief="flat")
        self.opp1_avatar.pack()
        self.opp1_cards_frame = tk.Frame(self.opp1_frame)
        self.opp1_cards_frame.pack()

        # Opponent 2
        self.opp2_frame = ttk.Frame(self.opponents_frame)
        self.opp2_frame.pack(side="left", padx=40)
        self.opp2_avatar = tk.Label(self.opp2_frame, text="O2", width=6, height=3, relief="flat")
        self.opp2_avatar.pack()
        self.opp2_cards_frame = tk.Frame(self.opp2_frame)
        self.opp2_cards_frame.pack()

        # Player hand display (images)
        self.player_frame = ttk.Frame(self.container)
        self.player_frame.pack(fill="x", pady=(6, 4))
        self.player_cards_frame = tk.Frame(self.player_frame)
        self.player_cards_frame.pack()

        # Advice panel
        self.advice_label = tk.Label(self.container, text="Conseil: -", font=("Helvetica", 10, "bold"), fg="blue", anchor="w", justify="left")
        self.advice_label.pack(fill="x", pady=(4, 6))

        # Cache for card images
        self.card_images = {}
        self.images_dir = os.path.join(os.path.dirname(__file__), "card_cache")
        os.makedirs(self.images_dir, exist_ok=True)

        # Avatars and back image cache
        self.avatar_images = {}
        self.card_back = None

        # Start background prefetch of full deck images
        try:
            threading.Thread(target=self._prefetch_deck_images, daemon=True).start()
        except Exception:
            pass

    def draw_cards(self, frame, cards_str_list, title):
        for widget in frame.winfo_children():
            widget.destroy()

        tk.Label(frame, text=title, font=("Helvetica", 10, "bold")).pack(side="top", pady=2)

        cards_frame = tk.Frame(frame, bg="#35654d", padx=5, pady=5, relief="ridge", bd=2)
        cards_frame.pack(side="bottom")

        suits = {'s': ('♠', 'black'), 'h': ('♥', '#d60000'), 'd': ('♦', '#d60000'), 'c': ('♣', 'black')}

        imgs = []
        for c in cards_str_list:
            img = None
            try:
                img = self._get_card_photo(c)
            except Exception:
                img = None

            if img:
                lbl = tk.Label(cards_frame, image=img, bd=1, relief="raised")
                lbl.image = img
                lbl.pack(side="left", padx=3)
                imgs.append(img)
            else:
                if len(c) == 2:
                    val, suit = c[0].upper(), c[1].lower()
                    if val == 'T':
                        val = '10'
                    symbol, color = suits.get(suit, ('?', 'black'))
                    card_lbl = tk.Label(
                        cards_frame,
                        text=f"{val}\n{symbol}",
                        font=("Arial", 16, "bold"),
                        bg="white",
                        fg=color,
                        relief="solid",
                        borderwidth=1,
                        width=3,
                        height=2,
                    )
                    card_lbl.pack(side="left", padx=3)
                else:
                    card_lbl = tk.Label(
                        cards_frame,
                        text=c,
                        font=("Arial", 14),
                        bg="white",
                        relief="solid",
                        borderwidth=1,
                        width=4,
                        height=2,
                    )
                    card_lbl.pack(side="left", padx=3)

        self.card_image_refs[frame] = imgs

    def _card_to_str(self, card):
        """Convert a treys card int to a display string, with a safe fallback."""
        try:
            from treys import Card as TreysCard
        except Exception:
            TreysCard = Card

        try:
            if TreysCard is not None:
                return TreysCard.int_to_str(card)
        except Exception:
            pass

        return str(card)

    def toggle_training(self):
        if not self.training_running:
            self.training_running = True
            self.btn_train.config(text="Arreter entrainement")
            self.lbl_train_status.config(text="Statut : en cours")
            threading.Thread(target=self.run_training_loop, daemon=True).start()
        else:
            self.training_running = False
            self.btn_train.config(text="Demarrer entrainement")
            self.lbl_train_status.config(text="Statut : arrete")

    def run_training_loop(self):
        try:
            from treys import Deck, Card, Evaluator
        except Exception:
            self.root.after(0, lambda: messagebox.showerror("Erreur", "La librairie 'treys' n'est pas installee."))
            self.training_running = False
            self.root.after(0, lambda: self.btn_train.config(text="Demarrer entrainement"))
            self.root.after(0, lambda: self.lbl_train_status.config(text="Statut : arrete"))
            return

        evaluator = Evaluator()
        round_num = 0
        while self.training_running:
            round_num += 1
            deck = Deck()
            hands = [deck.draw(2) for _ in range(3)]

            # Show player cards and opponents card backs initially
            try:
                self.root.after(0, lambda h0=hands[0]: self._show_player_cards(h0))
                self.root.after(0, lambda h1=hands[1]: self._show_opponent_cards(1, h1, reveal=False))
                self.root.after(0, lambda h2=hands[2]: self._show_opponent_cards(2, h2, reveal=False))
            except Exception:
                pass

            seats = ["Dealer", "SB", "BB"]
            random.shuffle(seats)
            player_role = seats[0]
            roles_text = f"Vous: {player_role} | Opp1: {seats[1]} | Opp2: {seats[2]}"

            def to_str(hand):
                try:
                    return " ".join([self._card_to_str(c) for c in hand])
                except Exception:
                    return " ".join(str(c) for c in hand)

            your_hand_str = to_str(hands[0])

            # Read user options
            try:
                start_blinds = float(self.entry_start_blinds.get())
            except Exception:
                start_blinds = 25.0
            try:
                sb_val = float(self.entry_sb.get())
            except Exception:
                sb_val = 0.5
            try:
                bb_val = float(self.entry_bb.get())
            except Exception:
                bb_val = 1.0

            # Estimate pre-action win%
            win_pct = self.estimate_win_rate(hands[0], [], 2, simulations=800)

            roles_text_full = f"{roles_text} | Start: {start_blinds}BB | SB: {sb_val} | BB: {bb_val}"
            self.current_round = {
                "round": round_num,
                "hands": hands,
                "roles_text": roles_text_full,
                "your_hand_str": your_hand_str,
                "win_pct": win_pct,
                "start_blinds": start_blinds,
                "sb": sb_val,
                "bb": bb_val,
            }
            self.selected_action = None
            self.wait_for_action = threading.Event()

            self.root.after(0, lambda: self._update_training_ui(round_num, roles_text_full, your_hand_str, win_pct, "En attente de votre action..."))

            self.wait_for_action.wait()

            if not self.training_running:
                break

            action = self.selected_action

            # Initialize stacks and pot
            starting_stack = int(start_blinds * bb_val)
            stacks = [starting_stack, starting_stack, starting_stack]

            # For simplicity: hands[0]=you, hands[1]=opp1, hands[2]=opp2
            stacks[1] -= sb_val
            stacks[2] -= bb_val
            pot = sb_val + bb_val

            self.root.after(0, lambda: self.lbl_pot.config(text=f"Pot: {pot}"))
            self.root.after(0, lambda: self.lbl_stacks.config(text=f"Stacks - Vous: {stacks[0]} | Opp1: {stacks[1]} | Opp2: {stacks[2]}"))

            self.root.after(0, lambda: self._update_community_ui([]))

            # Betting rounds: preflop, flop, turn, river
            board = []
            streets = [("Preflop", 0), ("Flop", 3), ("Turn", 1), ("River", 1)]
            alive = [True, True, True]

            for street_name, draw_count in streets:
                if draw_count > 0:
                    drawn = deck.draw(draw_count)
                    if isinstance(drawn, list):
                        board.extend(drawn)
                    else:
                        board.append(drawn)
                    self.root.after(0, lambda b=list(board): self._update_community_ui(b))

                if alive.count(True) == 1:
                    break

                win_pct_street = self.estimate_win_rate(hands[0], board, 2, simulations=400)
                self.selected_action = None
                self.wait_for_action = threading.Event()
                self.root.after(
                    0,
                    lambda rn=round_num, rt=roles_text_full, hs=your_hand_str, wp=win_pct_street:
                    self._update_training_ui(rn, rt + f" [{street_name}]", hs, wp, "A vous de jouer"),
                )

                # Bots decide in background (simple probability)
                bot_actions = [None, None]
                for i in (1, 2):
                    if not alive[i]:
                        bot_actions[i - 1] = "fold"
                        continue

                    cont_prob = min(max(win_pct_street / 100.0, 0.05), 0.95)
                    if random.random() < cont_prob:
                        bot_actions[i - 1] = "bet" if random.random() < 0.25 else "call"
                    else:
                        bot_actions[i - 1] = "fold"

                self.wait_for_action.wait()
                action = self.selected_action or "check"

                if action == "fold":
                    alive[0] = False
                elif action in ("raise", "call"):
                    bet = bb_val
                    if stacks[0] >= bet:
                        stacks[0] -= bet
                        pot += bet

                for idx, bot_action in enumerate(bot_actions, start=1):
                    if bot_action == "fold":
                        alive[idx] = False
                    elif bot_action in ("call", "bet"):
                        bet = bb_val if bot_action == "call" else bb_val * 2
                        if stacks[idx] >= bet:
                            stacks[idx] -= bet
                            pot += bet

                self.root.after(
                    0,
                    lambda p=pot, s=stacks: (
                        self.lbl_pot.config(text=f"Pot: {p}"),
                        self.lbl_stacks.config(text=f"Stacks - Vous: {s[0]} | Opp1: {s[1]} | Opp2: {s[2]}"),
                    ),
                )

                for _ in range(6):
                    if not self.training_running:
                        break
                    threading.Event().wait(0.15)

                if alive.count(True) == 1:
                    break

            # Showdown if needed
            if alive[0]:
                if alive.count(True) == 1:
                    result = "win"
                else:
                    my_score = evaluator.evaluate(board, hands[0])
                    opp_scores = [evaluator.evaluate(board, h) for h in (hands[1], hands[2])]
                    best_opp = min(opp_scores)
                    if my_score < best_opp:
                        result = "win"
                    elif my_score == best_opp:
                        result = "tie"
                    else:
                        result = "loss"
            else:
                result = "loss"

            # Reveal opponent cards at showdown
            try:
                self.root.after(0, lambda h1=hands[1]: self._show_opponent_cards(1, h1, reveal=True))
                self.root.after(0, lambda h2=hands[2]: self._show_opponent_cards(2, h2, reveal=True))
            except Exception:
                pass

            analysis = self.analyze_decision(action, win_pct, result)
            board_str = " ".join([self._card_to_str(c) for c in board]) if board else "--"
            summary = (
                f"Round {round_num}: Action={action} | Win% pre-action={win_pct:.1f}% | "
                f"Resultat={result.upper()} | Board: {board_str} | Pot: {pot}"
            )
            self.root.after(0, lambda s=summary, a=analysis: self._post_round_update(s, a))

        self.root.after(0, lambda: self.lbl_train_status.config(text="Statut : arrete"))

    def _update_training_ui(self, round_num, roles_text, hand_str, win_pct, advice):
        self.lbl_train_status.config(text=f"Statut : en cours (round {round_num})")
        self.lbl_train_roles.config(text=f"Positions : {roles_text}")
        self.lbl_train_hand.config(text=f"Main (vous) : {hand_str}")
        self.lbl_train_win.config(text=f"Win% estime : {win_pct:.2f}% - Conseil: {advice}")
        self.advice_label.config(text=f"Conseil: {advice}")

        try:
            if self.current_round and "hands" in self.current_round:
                self._show_player_cards(self.current_round["hands"][0])
        except Exception:
            pass

    def _post_round_update(self, summary, analysis):
        self.txt_train_log.insert("end", summary + "\n")
        self.txt_train_log.insert("end", "Analyse: " + analysis + "\n\n")
        self.txt_train_log.see("end")

    def _update_community_ui(self, board):
        cards = []
        for card in board:
            try:
                cards.append(self._card_to_str(card))
            except Exception:
                cards.append(str(card))

        if cards:
            self.draw_cards(self.community_cards_frame, cards, "Table")
        else:
            for widget in self.community_cards_frame.winfo_children():
                widget.destroy()

    def _get_card_back(self):
        """Return a PhotoImage for the back of a card (cached)."""
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

    def _get_avatar_photo(self, name, idx):
        """Return a small avatar PhotoImage for a player (cached)."""
        key = f"avatar_{idx}"
        if key in self.avatar_images:
            return self.avatar_images[key]

        local_path = os.path.join(self.images_dir, f"{key}.png")
        if not os.path.exists(local_path):
            url = f"https://robohash.org/{name}.png?size=64x64"
            try:
                urllib.request.urlretrieve(url, local_path)
            except Exception:
                return None

        try:
            img = tk.PhotoImage(file=local_path)
            self.avatar_images[key] = img
            return img
        except Exception:
            return None

    def _show_opponent_cards(self, opp_index, hand, reveal=False):
        """opp_index: 1 or 2. If reveal False show back, else show faces."""
        if opp_index == 1:
            avatar_lbl = self.opp1_avatar
            frame = self.opp1_cards_frame
        else:
            avatar_lbl = self.opp2_avatar
            frame = self.opp2_cards_frame

        av = self._get_avatar_photo(f"opp{opp_index}", opp_index)
        if av:
            avatar_lbl.config(image=av, text="")
            avatar_lbl.image = av

        cards = []
        if hand and reveal:
            for card in hand:
                try:
                    cards.append(self._card_to_str(card))
                except Exception:
                    cards.append(str(card))
        elif hand:
            cards = ["XX" for _ in hand]

        if cards:
            self.draw_cards(frame, cards, f"Opp{opp_index}")
        else:
            for widget in frame.winfo_children():
                widget.destroy()

    def _show_player_cards(self, hand):
        """Display player hole cards as images, fallback to short text."""
        cards = []
        if hand:
            for card in hand:
                try:
                    cards.append(self._card_to_str(card))
                except Exception:
                    cards.append(str(card))

        if cards:
            self.draw_cards(self.player_cards_frame, cards, "Votre Main")
        else:
            for widget in self.player_cards_frame.winfo_children():
                widget.destroy()

    def _get_card_photo(self, card_str):
        """Return a tk.PhotoImage for a card like Ah or None on failure. Caches images locally."""
        s = card_str.strip().replace("[", "").replace("]", "").replace(",", "")
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

        local_path = os.path.join(self.images_dir, f"{code}.png")
        if code in self.card_images:
            return self.card_images[code]

        if not os.path.exists(local_path):
            url = f"https://deckofcardsapi.com/static/img/{code}.png"
            try:
                urllib.request.urlretrieve(url, local_path)
            except Exception:
                return None

        try:
            img = tk.PhotoImage(file=local_path)
            try:
                w = img.width()
                target = 72
                if w > target:
                    factor = max(1, int(w / target))
                    img = img.subsample(factor, factor)
            except Exception:
                pass

            self.card_images[code] = img
            return img
        except Exception:
            return None

    def _prefetch_deck_images(self):
        """Download all 52 card images and back image in background."""
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

    def on_raise(self):
        if self.wait_for_action is None:
            return
        self.selected_action = "raise"
        self.wait_for_action.set()

    def on_call(self):
        if self.wait_for_action is None:
            return
        self.selected_action = "call"
        self.wait_for_action.set()

    def on_fold(self):
        if self.wait_for_action is None:
            return
        self.selected_action = "fold"
        self.wait_for_action.set()

    def analyze_decision(self, action, win_pct, result):
        """Basic analysis of player decision."""
        msg = []

        if action == "raise":
            if win_pct >= 55:
                msg.append("Relance raisonnable: forte equite pre-flop.")
            elif win_pct >= 35:
                msg.append("Relance agressive: equite moyenne, attention au sizing.")
            else:
                msg.append("Relance risquee: faible equite, generalement deconseillee.")
        elif action == "call":
            if win_pct >= 45:
                msg.append("Call acceptable: tu as une equite correcte pour suivre.")
            else:
                msg.append("Call passif: faible equite, fold souvent preferable.")
        elif action == "fold":
            if win_pct >= 50:
                msg.append("Fold discutable: tu avais une bonne equite, probablement a jouer.")
            else:
                msg.append("Fold prudent: tu avais peu d'equite, fold approprie.")

        if result == "win":
            msg.append("Resultat: tu as gagne la main.")
        elif result == "loss":
            msg.append("Resultat: tu as perdu la main.")
        else:
            msg.append("Resultat: egalite.")

        return " ".join(msg)

    def estimate_win_rate(self, my_hand, board_partial, nb_opponents, simulations=1000):
        try:
            from treys import Deck, Evaluator
        except Exception:
            return 0.0

        evaluator = Evaluator()
        wins = 0
        ties = 0

        base_deck = Deck()
        for card in my_hand + board_partial:
            if card in base_deck.cards:
                base_deck.cards.remove(card)

        for _ in range(simulations):
            deck = Deck()
            deck.cards = [c for c in base_deck.cards]
            opps = [deck.draw(2) for _ in range(nb_opponents)]

            cards_to_draw = 5 - len(board_partial)
            board = list(board_partial)
            if cards_to_draw > 0:
                drawn = deck.draw(cards_to_draw)
                if isinstance(drawn, list):
                    board.extend(drawn)
                else:
                    board.append(drawn)

            my_score = evaluator.evaluate(board, my_hand)
            opp_scores = [evaluator.evaluate(board, opp) for opp in opps]
            best_opp = min(opp_scores)
            if my_score < best_opp:
                wins += 1
            elif my_score == best_opp:
                ties += 1

        win_rate = (wins / simulations) * 100
        tie_rate = (ties / simulations) * 100
        return win_rate + tie_rate * 0.5
